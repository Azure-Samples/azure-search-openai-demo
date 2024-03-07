import json

import pytest
from openai.types.chat import ChatCompletion

from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach


@pytest.fixture
def chat_approach():
    return ChatReadRetrieveReadApproach(
        search_client=None,
        auth_helper=None,
        openai_client=None,
        chatgpt_model="gpt-35-turbo",
        chatgpt_deployment="chat",
        embedding_deployment="embeddings",
        embedding_model="text-",
        sourcepage_field="",
        content_field="",
        query_language="en-us",
        query_speller="lexicon",
    )


def test_get_search_query(chat_approach):
    payload = """
    {
	"id": "chatcmpl-81JkxYqYppUkPtOAia40gki2vJ9QM",
	"object": "chat.completion",
	"created": 1695324963,
	"model": "gpt-35-turbo",
	"prompt_filter_results": [
		{
			"prompt_index": 0,
			"content_filter_results": {
				"hate": {
					"filtered": false,
					"severity": "safe"
				},
				"self_harm": {
					"filtered": false,
					"severity": "safe"
				},
				"sexual": {
					"filtered": false,
					"severity": "safe"
				},
				"violence": {
					"filtered": false,
					"severity": "safe"
				}
			}
		}
	],
	"choices": [
		{
			"index": 0,
			"finish_reason": "function_call",
			"message": {
				"content": "this is the query",
				"role": "assistant",
				"tool_calls": [
					{
                        "id": "search_sources1235",
						"type": "function",
						"function": {
							"name": "search_sources",
							"arguments": "{\\n\\"search_query\\":\\"accesstelemedicineservices\\"\\n}"
						}
					}
				]
			},
			"content_filter_results": {

			}
		}
	],
	"usage": {
		"completion_tokens": 19,
		"prompt_tokens": 425,
		"total_tokens": 444
	}
}
"""
    default_query = "hello"
    chatcompletions = ChatCompletion.model_validate(json.loads(payload), strict=False)
    query = chat_approach.get_search_query(chatcompletions, default_query)

    assert query == "accesstelemedicineservices"


def test_get_search_query_returns_default(chat_approach):
    payload = '{"id":"chatcmpl-81JkxYqYppUkPtOAia40gki2vJ9QM","object":"chat.completion","created":1695324963,"model":"gpt-35-turbo","prompt_filter_results":[{"prompt_index":0,"content_filter_results":{"hate":{"filtered":false,"severity":"safe"},"self_harm":{"filtered":false,"severity":"safe"},"sexual":{"filtered":false,"severity":"safe"},"violence":{"filtered":false,"severity":"safe"}}}],"choices":[{"index":0,"finish_reason":"function_call","message":{"content":"","role":"assistant"},"content_filter_results":{}}],"usage":{"completion_tokens":19,"prompt_tokens":425,"total_tokens":444}}'
    default_query = "hello"
    chatcompletions = ChatCompletion.model_validate(json.loads(payload), strict=False)
    query = chat_approach.get_search_query(chatcompletions, default_query)

    assert query == default_query


def test_get_messages_from_history(chat_approach):
    messages = chat_approach.get_messages_from_history(
        system_prompt="You are a bot.",
        model_id="gpt-35-turbo",
        history=[
            {"role": "user", "content": "What happens in a performance review?"},
            {
                "role": "assistant",
                "content": "During the performance review at Contoso Electronics, the supervisor will discuss the employee's performance over the past year and provide feedback on areas for improvement. They will also provide an opportunity for the employee to discuss their goals and objectives for the upcoming year. The review is a two-way dialogue between managers and employees, and employees will receive a written summary of their performance review which will include a rating of their performance, feedback, and goals and objectives for the upcoming year [employee_handbook-3.pdf].",
            },
            {"role": "user", "content": "What does a Product Manager do?"},
        ],
        user_content="What does a Product Manager do?",
        max_tokens=3000,
    )
    assert messages == [
        {"role": "system", "content": "You are a bot."},
        {"role": "user", "content": "What happens in a performance review?"},
        {
            "role": "assistant",
            "content": "During the performance review at Contoso Electronics, the supervisor will discuss the employee's performance over the past year and provide feedback on areas for improvement. They will also provide an opportunity for the employee to discuss their goals and objectives for the upcoming year. The review is a two-way dialogue between managers and employees, and employees will receive a written summary of their performance review which will include a rating of their performance, feedback, and goals and objectives for the upcoming year [employee_handbook-3.pdf].",
        },
        {"role": "user", "content": "What does a Product Manager do?"},
    ]


def test_get_messages_from_history_truncated(chat_approach):
    messages = chat_approach.get_messages_from_history(
        system_prompt="You are a bot.",
        model_id="gpt-35-turbo",
        history=[
            {"role": "user", "content": "What happens in a performance review?"},
            {
                "role": "assistant",
                "content": "During the performance review at Contoso Electronics, the supervisor will discuss the employee's performance over the past year and provide feedback on areas for improvement. They will also provide an opportunity for the employee to discuss their goals and objectives for the upcoming year. The review is a two-way dialogue between managers and employees, and employees will receive a written summary of their performance review which will include a rating of their performance, feedback, and goals and objectives for the upcoming year [employee_handbook-3.pdf].",
            },
            {"role": "user", "content": "What does a Product Manager do?"},
        ],
        user_content="What does a Product Manager do?",
        max_tokens=10,
    )
    assert messages == [
        {"role": "system", "content": "You are a bot."},
        {"role": "user", "content": "What does a Product Manager do?"},
    ]


def test_get_messages_from_history_truncated_longer(chat_approach):
    messages = chat_approach.get_messages_from_history(
        system_prompt="You are a bot.",  # 8 tokens
        model_id="gpt-35-turbo",
        history=[
            {"role": "user", "content": "What happens in a performance review?"},  # 10 tokens
            {
                "role": "assistant",
                "content": "During the performance review at Contoso Electronics, the supervisor will discuss the employee's performance over the past year and provide feedback on areas for improvement. They will also provide an opportunity for the employee to discuss their goals and objectives for the upcoming year. The review is a two-way dialogue between managers and employees, and employees will receive a written summary of their performance review which will include a rating of their performance, feedback, and goals and objectives for the upcoming year [employee_handbook-3.pdf].",
            },  # 102 tokens
            {"role": "user", "content": "Is there a dress code?"},  # 9 tokens
            {
                "role": "assistant",
                "content": "Yes, there is a dress code at Contoso Electronics. Look sharp! [employee_handbook-1.pdf]",
            },  # 26 tokens
            {"role": "user", "content": "What does a Product Manager do?"},  # 10 tokens
        ],
        user_content="What does a Product Manager do?",
        max_tokens=55,
    )
    assert messages == [
        {"role": "system", "content": "You are a bot."},
        {"role": "user", "content": "Is there a dress code?"},
        {
            "role": "assistant",
            "content": "Yes, there is a dress code at Contoso Electronics. Look sharp! [employee_handbook-1.pdf]",
        },
        {"role": "user", "content": "What does a Product Manager do?"},
    ]


def test_get_messages_from_history_truncated_break_pair(chat_approach):
    """Tests that the truncation breaks the pair of messages."""
    messages = chat_approach.get_messages_from_history(
        system_prompt="You are a bot.",  # 8 tokens
        model_id="gpt-35-turbo",
        history=[
            {"role": "user", "content": "What happens in a performance review?"},  # 10 tokens
            {
                "role": "assistant",
                "content": "The supervisor will discuss the employee's performance and provide feedback on areas for improvement. They will also provide an opportunity for the employee to discuss their goals and objectives for the upcoming year. The review is a two-way dialogue between managers and employees, and employees will receive a written summary of their performance review which will include a rating of their performance, feedback, and goals for the upcoming year [employee_handbook-3.pdf].",
            },  # 87 tokens
            {"role": "user", "content": "Is there a dress code?"},  # 9 tokens
            {
                "role": "assistant",
                "content": "Yes, there is a dress code at Contoso Electronics. Look sharp! [employee_handbook-1.pdf]",
            },  # 26 tokens
            {"role": "user", "content": "What does a Product Manager do?"},  # 10 tokens
        ],
        user_content="What does a Product Manager do?",
        max_tokens=147,
    )
    assert messages == [
        {"role": "system", "content": "You are a bot."},
        {
            "role": "assistant",
            "content": "The supervisor will discuss the employee's performance and provide feedback on areas for improvement. They will also provide an opportunity for the employee to discuss their goals and objectives for the upcoming year. The review is a two-way dialogue between managers and employees, and employees will receive a written summary of their performance review which will include a rating of their performance, feedback, and goals for the upcoming year [employee_handbook-3.pdf].",
        },
        {"role": "user", "content": "Is there a dress code?"},
        {
            "role": "assistant",
            "content": "Yes, there is a dress code at Contoso Electronics. Look sharp! [employee_handbook-1.pdf]",
        },
        {"role": "user", "content": "What does a Product Manager do?"},
    ]


def test_get_messages_from_history_system_message(chat_approach):
    """Tests that the system message token count is considered."""
    messages = chat_approach.get_messages_from_history(
        system_prompt="Assistant helps the company employees with their healthcare plan questions, and questions about the employee handbook. Be brief in your answers.",  # 24 tokens
        model_id="gpt-35-turbo",
        history=[
            {"role": "user", "content": "What happens in a performance review?"},  # 10 tokens
            {
                "role": "assistant",
                "content": "During the performance review at Contoso Electronics, the supervisor will discuss the employee's performance over the past year and provide feedback on areas for improvement. They will also provide an opportunity for the employee to discuss their goals and objectives for the upcoming year. The review is a two-way dialogue between managers and employees, and employees will receive a written summary of their performance review which will include a rating of their performance, feedback, and goals and objectives for the upcoming year [employee_handbook-3.pdf].",
            },  # 102 tokens
            {"role": "user", "content": "Is there a dress code?"},  # 9 tokens
            {
                "role": "assistant",
                "content": "Yes, there is a dress code at Contoso Electronics. Look sharp! [employee_handbook-1.pdf]",
            },  # 26 tokens
            {"role": "user", "content": "What does a Product Manager do?"},  # 10 tokens
        ],
        user_content="What does a Product Manager do?",
        max_tokens=36,
    )
    assert messages == [
        {
            "role": "system",
            "content": "Assistant helps the company employees with their healthcare plan questions, and questions about the employee handbook. Be brief in your answers.",
        },
        {"role": "user", "content": "What does a Product Manager do?"},
    ]


def test_extract_followup_questions(chat_approach):
    content = "Here is answer to your question.<<What is the dress code?>>"
    pre_content, followup_questions = chat_approach.extract_followup_questions(content)
    assert pre_content == "Here is answer to your question."
    assert followup_questions == ["What is the dress code?"]


def test_extract_followup_questions_three(chat_approach):
    content = """Here is answer to your question.

<<What are some examples of successful product launches they should have experience with?>>
<<Are there any specific technical skills or certifications required for the role?>>
<<Is there a preference for candidates with experience in a specific industry or sector?>>"""
    pre_content, followup_questions = chat_approach.extract_followup_questions(content)
    assert pre_content == "Here is answer to your question.\n\n"
    assert followup_questions == [
        "What are some examples of successful product launches they should have experience with?",
        "Are there any specific technical skills or certifications required for the role?",
        "Is there a preference for candidates with experience in a specific industry or sector?",
    ]


def test_extract_followup_questions_no_followup(chat_approach):
    content = "Here is answer to your question."
    pre_content, followup_questions = chat_approach.extract_followup_questions(content)
    assert pre_content == "Here is answer to your question."
    assert followup_questions == []


def test_extract_followup_questions_no_pre_content(chat_approach):
    content = "<<What is the dress code?>>"
    pre_content, followup_questions = chat_approach.extract_followup_questions(content)
    assert pre_content == ""
    assert followup_questions == ["What is the dress code?"]


def test_get_messages_from_history_few_shots(chat_approach):
    user_query_request = "What does a Product manager do?"
    messages = chat_approach.get_messages_from_history(
        system_prompt=chat_approach.query_prompt_template,
        model_id=chat_approach.chatgpt_model,
        user_content=user_query_request,
        history=[],
        max_tokens=chat_approach.chatgpt_token_limit - len(user_query_request),
        few_shots=chat_approach.query_prompt_few_shots,
    )
    # Make sure messages are in the right order
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"
    assert messages[3]["role"] == "user"
    assert messages[4]["role"] == "assistant"
    assert messages[5]["role"] == "user"
    assert messages[5]["content"] == user_query_request
