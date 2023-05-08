import openai
from approaches.approach import Approach

# Simple ChatGPT experience that calls the Azure OpenAI APIs directly. The input history is converted to the chat/completions "messages" format and submitted to the model.
class ChatGPTReadApproach(Approach):

    def __init__(self, chatgpt_deployment: str): ## BDL: removed search_client, gpt_deployment, sourcepage_field, content_field as they're not needed for vanilla chatgptread
        self.chatgpt_deployment = chatgpt_deployment

    def run(self, history: list[dict], overrides: dict) -> any:

        ## add a system prompt to the messages
        ## then convert the input history to the chat/completions "messages" format
        
        ## if the systme override for the prompt is set, use that for the ssytem prompt. Otherwise, use the default
        prompt_override = overrides.get("prompt_template")
        if prompt_override is None:
            system_prompt = "You are an AI chatbot that responds to whatever the user says."
        else:
            system_prompt = prompt_override
        
        ## Use the "ChatCompletions" format for the input prompt messages.
        messages = [
            {"role": "system", "content": f"{system_prompt}"},
        ]

        for utterance_dict in history:
            ## check if the user key exists in the dict
            if "user" in utterance_dict:
                messages.append({"role": "user", "content": utterance_dict["user"]})
            ## then check if the "bot" key exists in the dict
            if "bot" in utterance_dict:
                messages.append({"role": "system", "content": utterance_dict["bot"]})
        
        openai.api_version = "2023-03-15-preview"

        completion = openai.ChatCompletion.create(    
            engine=self.chatgpt_deployment,
            messages=messages,
            temperature=overrides.get("temperature") or 0.7,
            max_tokens=1024 
        )

        return {"data_points": "There were no documents searched. This is vanilla", "answer": completion['choices'][0]['message']['content'], "thoughts": f"I have no thoughts, I'm a robot"}
    
    def get_chat_history_as_text(self, history, include_last_turn=True, approx_max_tokens=1000) -> str:
        history_text = ""
        for h in reversed(history if include_last_turn else history[:-1]):
            history_text = """<|im_start|>user""" +"\n" + h["user"] + "\n" + """<|im_end|>""" + "\n" + """<|im_start|>assistant""" + "\n" + (h.get("bot") + """<|im_end|>""" if h.get("bot") else "") + "\n" + history_text
            if len(history_text) > approx_max_tokens*4:
                break    
        return history_text