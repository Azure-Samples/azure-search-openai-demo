import logging

from httpx import HTTPStatusError
from pyrit.chat_message_normalizer import ChatMessageNop, ChatMessageNormalizer
from pyrit.common import net_utility
from pyrit.exceptions import (
    EmptyResponseException,
    RateLimitException,
    handle_bad_request_exception,
    pyrit_target_retry,
)
from pyrit.memory import MemoryInterface
from pyrit.models import (
    ChatMessage,
    PromptRequestResponse,
    construct_response_from_request,
)
from pyrit.prompt_target import PromptChatTarget

logger = logging.getLogger("evaluation")


class AppChatTarget(PromptChatTarget):

    def __init__(
        self,
        *,
        endpoint_uri: str,
        chat_message_normalizer: ChatMessageNormalizer = ChatMessageNop(),
        memory: MemoryInterface = None,
        target_parameters: dict,
    ) -> None:
        """Initialize an instance of the AppChatTarget class."""
        PromptChatTarget.__init__(self, memory=memory)

        self.endpoint_uri: str = endpoint_uri

        self.chat_message_normalizer = chat_message_normalizer

        self.target_parameters = target_parameters

    async def send_prompt_async(self, *, prompt_request: PromptRequestResponse) -> PromptRequestResponse:
        """Send a normalized prompt async to the target and return the response."""
        self._validate_request(prompt_request=prompt_request)
        request = prompt_request.request_pieces[0]

        messages = self._memory.get_chat_messages_with_conversation_id(conversation_id=request.conversation_id)

        messages.append(request.to_chat_message())

        logger.info(f"Sending the following prompt to the prompt target: {request}")

        try:
            resp_text = await self._complete_chat_async(messages=messages, target_parameters=self.target_parameters)

            if not resp_text:
                raise EmptyResponseException(message="The chat returned an empty response.")

            response_entry = construct_response_from_request(request=request, response_text_pieces=[resp_text])
        except HTTPStatusError as hse:
            if hse.response.status_code == 400:
                # Handle Bad Request
                response_entry = handle_bad_request_exception(response_text=hse.response.text, request=request)
            elif hse.response.status_code == 429:
                raise RateLimitException()
            else:
                raise hse

        logger.info(
            "Received the following response from the prompt target"
            + f"{response_entry.request_pieces[0].converted_value}"
        )
        return response_entry

    @pyrit_target_retry
    async def _complete_chat_async(self, messages: list[ChatMessage], target_parameters: dict) -> str:
        """Complete a chat interaction by generating a response to the given input prompt."""
        headers = self._get_headers()
        payload = self._construct_http_body(messages, target_parameters)

        response = await net_utility.make_request_and_raise_if_error_async(
            endpoint_uri=self.endpoint_uri, method="POST", request_body=payload, headers=headers
        )
        response_json = response.json()

        if (message_content := response_json.get("message", {}).get("content")) is None:
            raise ValueError("Message content not found in response.")

        return message_content

    def _construct_http_body(self, messages: list[ChatMessage], target_parameters: dict) -> dict:
        """Construct the HTTP request body for the application endpoint."""
        squashed_messages = self.chat_message_normalizer.normalize(messages)
        messages_dict = [message.model_dump() for message in squashed_messages]
        data = {
            "messages": [{"role": msg.get("role"), "content": msg.get("content")} for msg in messages_dict],
            "context": target_parameters,
        }
        return data

    def _get_headers(self) -> dict:
        """Construct headers for an HTTP request."""
        headers: dict = {
            "Content-Type": "application/json",
        }

        return headers

    def _validate_request(self, *, prompt_request: PromptRequestResponse) -> None:
        """Validate a prompt request."""
        if len(prompt_request.request_pieces) != 1:
            raise ValueError("This target only supports a single prompt request piece.")

        if prompt_request.request_pieces[0].converted_value_data_type != "text":
            raise ValueError("This target only supports text prompt input.")
