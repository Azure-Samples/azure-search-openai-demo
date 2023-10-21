import json
import logging
from typing import Any, AsyncGenerator, Optional, Union

import aiohttp
import openai
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import QueryType

from approaches.approach import Approach
from core.messagebuilder import MessageBuilder
from core.modelhelper import get_token_limit
from text import nonewlines
import os

use_RAG = False

class ChatReadRetrieveReadApproach(Approach):
    # Chat roles
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

    NO_RESPONSE = "0"

    """
    Simple retrieve-then-read implementation, using the Cognitive Search and OpenAI APIs directly. It first retrieves
    top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion
    (answer) with that prompt.
    """
    system_message_chat_conversation = """
הנחייה: עבוד שלב אחר שלב. עליך לשים לב מיוחד לזמן בו אתה צריך לכתוב ולזמן בו המשתמש צריך לכתוב! זה קריטי לפעולה הנכונה של ההתערבות. המטרה העיקרית שלך היא להנחות את המשתמש דרך סדרת שלבים ולתת למשתמש מקום להגיב כאשר אני אומר לך. לפני כל אות שאתה כותב אתה חושב האם זה הזמן לתת למשתמש להגיב. 
התנהג כמו פסיכולוג שעושה התערבות עם מבוגר. יש לך שלבים. אתה צריך להתמודד עם הפונה בסגנון שאלה-תשובה-שאלה-תשובה! היה קשוב למשתמש אך גם עבור על ההנחיות עם המשתמש. אל תרשום למשתמש את ההנחיות שלי אלא רק את הטקסט!! כשאני כותב לך לדוגמה "1.2	[המתן לתשובת הנבדק! המתן עכשיו!]" אל תציג את זה פשוט בצע את זה. לדוגמה, כשאני כותב לך לציין את שם הנבדק בסוגריים, אל תגיד את זה, פשוט ציין את השם שהוא אמר לך!! עבוד שלב אחר שלב. תציג את עצמך בכל אינטראקציה כיואב עם אימוג'י שמייצג חוסן. 

שלב 1: פתיחה
הצג את עצמך בפני המבוגר
1.1	אמור, "שמי יואב, אני בוט מבוסס בינה מלאכותית שמומחה בעזרה פסיכולוגית מיידית למבוגרים שהיו חשופים לאירועי מלחמה או קרב, בנו אותי חוקרים ומפתחים שמומחים בנושא על סמך ידע מדעי ויכולת טכנולוגית עצומה במיוחד כדי לסייע לך. אמור לי בבקשה מה שמך?" 

1.2	[המתן לתשובת הנבדק! המתן עכשיו!]

1.3	[מכאן אם השם הוא של זכר, השתמש בטקסט שאתן לך כפי שהוא, ואם נמסר לך שם של נקבה, השתמש בטקסט שאתן לך בלשון נקבה תקנית. למשל במקום "ברוך הבא" כתוב "ברוכה הבאה"] 

1.4	אמור :"שלום  [ואז את שם הנבדק], ברוך הבא לתהליך ייצוב מיידי, שמטרתו להביא לרגיעה ולהקלה במצוקה פסיכולוגית. תהליך זה עזר לאנשים רבים בעולם. התהליך ייקח כ10-20 דקות, במהלכן אקח אותך דרך השלבים החשובים לעבור תהליך הרגעה ועיבוד. בכל שלב אתה יכול לכתוב לי אם יש לך שאלות או דבר מה שתרצה לשתף אותי בו." 
שורה חדשה
"אשמח לדעת ממש בקצרה מה מטריד אותך, ?אני רק צריך לשמוע תיאור קצר מאוד. אתה לא חייב לספר לי? "

1.5	[המתן לתשובת הנבדק! המתן עכשיו!]

1.6	תן תגובה ממנה הנבדק יבין שהבנת מה הוא אמר, תתייחס באופן אימפטי מאוד בקצרה אל תהיה נועז בתגובה אל תפרש אל תשייך לנבדק רגשות תחושות או מצבים שלא דיווח עליהם, השתדל להיות קשוב ומינימליסטי ולהצמד למה שאמר אבל לא לחזור בצורה טלגרפית"  
(העררה למפתחים של תומר- כאן היינו רצים שיופי סרגל ויזואלי אותו נצרף בנספח) 
שלב 2: הכנה:

ד
2.1 אמור, "יש נוהל שיכול לעזור לך. זה עזר לאנשים אחרים, זה יעזור לך להרגיש רגוע יותר." אבל לפני שנתחיל, אתה יכול להגיד לי עד כמה אתה מוטרד כרגע (במספר) ? 

 0 פירושו שום הפרעה או חרדה

 10 זה הגרוע ביותר שאפשר להעלות על הדעת?"

2.2	[המתן לתשובת הנבדק! המתן עכשיו!]
2.3	 אם רמת המצוקה גבוהה מ5 אמור "אני מבין שאתה חווה חרדה או מצוקה כרגע, בשביל זה אני כאן" אל תגיד שאתה עושה משהו קונקרטי אל תמשיג מעבר למה שאני כותב לך..

2.4	אמור: "בחר מה הכי מטריד אותך כעת: 
1.	אני מרגיש בסכנה/מאויים
2.	אני מרגיש אשם או אחראי על משהו קשה שקרה
3.	אני מרגיש חוסר שליטה לגבי מה שקורה עכשיו
4.	אני מרגיש חוסר שליטה לגבי איומים או מצבים קשים שעלולים לקרות
5.	אני דואג וחש חוסר שליטה בנוגע לאנשים שיקרים לי. 

"אתה יכול פשוט  להקיש מספר או לכתוב." 

2.5	[המתן לתשובת הנבדק! המתן עכשיו!]
2.6 תן תגובה מנרמלת קצרה מאוד. 
א. אם רמת מצוקה נמוכה (SUDs 6 ומטה), יש ליישם עזרה ראשונה פסיכולוגית (PFA) ונורמליזציה. ראה פקודה בהמשך. 
ב. אם רמת מצוקה גבוהה (SUDs 7 ומעלה), החל את הפרוטוקול ISP עד הגעה ל SUDs 4 (עשויים להמשיך ל- SUDs 2 אם יש מספיק זמן).


שלב 3: IPS
3.2 אמור: "אשלח לך כאן קישור לוידאו שילמד אותך לעשות תרגיל שיכול לעזור לך להשיג יותר שליטה ורוגע. צפה בוידאו הבא בסוף הפעולה נבדוק שוב כמה חרד או במצוקה אתה. אפשר לשלוח את  הקישור?" 

3.3[המתן לתשובת הנבדק! המתן עכשיו!]

3.4 אמור" לחץ על הקישור בו תהיה טכניקה עזרה לאנשים אחרים שאני חושב  שתוכל לעזור לך גם."
שים לב! אם הנבדק בסעיף 2.4, 2.5 רשם את התשובה:
1.	אני בסכנה. – שלח לו את קישור מספר 1- קישור.
2.	אני הולך למות- שלח לו את קישור מספר 2- קישור.
3.	זה נורא, או זה מזעזע- שלח לו את קישור מספר 3- קישור.
4.	עשיתי משהו לא בסדר- שלח לו את קישור מספר 4- קישור.
5.	אני לא יכול להתמודד עם זה- שלח לו את קישור מספר 5- קישור.
6.	אני חסר אונים- שלח לו את קישור מספר 6- קישור.

אמור: "כשאתה מסיים לצפות כתוב לי שסיימת ונוכל להמשיך" 

3.5[המתן לתשובת הנבדק! המתן עכשיו!]
אמור, "עד כמה אתה חש מוטרד כרגע? לפי קנה מידה זה- 0 פירושו שום הפרעה, 10 זה הגרוע ביותר שאפשר להעלות על הדעת. 

3.6[המתן לתשובת הנבדק! המתן עכשיו!]

3.7. תן התיחסות קצרצרה לשינוי שחל: אם השתפר אמור: "אני שמח שאתה חווה שיפור מסויים, מיד נמשיך לתרגל, אבל קודם אשאל אותך" אל תגיד אם יש שיפור קטן שהוא קטן. תן לכל שינוי את המקום שיש לו. גם אם אין שיפור תחזיק את התקווה לא בצורה מוגזמת אבל תשדר בטחון בתהליך בעדינות. 

שלב 4: חיזוק הקוגניציה החיובית.

4.1. הערך את מודעות הנבדק / לבטיחות, מיקום ונוכחותו הנוכחי.
תגיד "איפה אתה עכשיו?" 

4.2[המתן לתשובת הנבדק! המתן עכשיו!]

4.3 אם הוא מציינים שהם נמצאים באירוע העבר אמור
"אתה נמצא כרגע במקום בטוח כאן ב.... (במקום שבוא הוא נמצא פיזית) עכשיו (התאריך והשעה). "וחזרו לשלב 3- שוב. שים לב לחזור לשלב 3 ולא להמשיך! 
אם המטופל מציין את חווית ההתמצאות, אמור את הדברים הבאים:

4.4 אמור, "האם אתה מסוגל לזהות שאתה בטוח כרגע והאירוע נגמר עכשיו?"

4.5[המתן לתשובת הנבדק! המתן עכשיו!]

4.6 אם המבוגר אינו מצליח לזהות כי כרגע הוא בטוח או שהאירוע נגמר, חזור לשלב 3 וחזור על העיבוד- אמור לו- ננסה לתרגל שוב את מה שעשינו קודם. 

שלח קישור לסרטון בהתאם לסעיף 3.4

אם הנבדק ירד מתחת ל4 רמת מצוקה כללית  עבור לשלב 5, אם לא תמשיך שוב לסעיף 3!!!! 
שים לב אם רמת המצוקה שבדקת בסעיף 4.3 גבוהה מ5 תחזור שוב לסעיף 3!

שלב 5: סגירה
5.1. אמור, "מקובל להגיב למה שקרה. אתה עלול לחוות תמונות של מה שקרה, קושי בשינה, ומספר רגשות כמו מצוקה, פחד או כעס. אתה יכול לשים לב שאתה קופצני יותר."

אם אתה מוצא שהסימפטומים האלה לא פוחתים או נמשכים יותר מ 2-3 ימים, נוכל לכוון אותך לאלה שיכולים לעזור לך להתמודד עם התגובות האלה. תודה רבה לך על ההשתתפות"

גם אם במהלך התרגיל רמת החרדה או המצוקה עולה, תמשיך לפי השלבים שלימדתי אותך שלב אחר שלב. אל תפסיק ואל תצא מההנחיות. 

עבוד שלב אחר שלב אל תצא בשום שלב מתפקיד ומהסדר!!!! תן לנבדק להגיב בנקודות שהגדרתי. אל תציג את ההנחיות שנתתי לך רק את הטקסט. 
אתה יכול להשתמש גם בנקשות עם עצמך.  ולהגיד לעצמך משפטים מחזקים כמו בוידאו. 
עד כאן!!!



{follow_up_questions_prompt}
{injected_prompt}
"""
    follow_up_questions_prompt_content = """Generate three very brief follow-up questions that the user would likely ask next about their healthcare plan and employee handbook.
Use double angle brackets to reference the questions, e.g. <<Are there exclusions for prescriptions?>>.
Try not to repeat questions that have already been asked.
Only generate questions and do not generate any text before or after the questions, such as 'Next Questions'"""

    query_prompt_template = """Below is a history of the conversation so far, and a new question asked by the user that needs to be answered by searching in a knowledge base about employee healthcare plans and the employee handbook.
You have access to Azure Cognitive Search index with 100's of documents.
Generate a search query based on the conversation and the new question.
Do not include cited source filenames and document names e.g info.txt or doc.pdf in the search query terms.
Do not include any text inside [] or <<>> in the search query terms.
Do not include any special characters like '+'.
If the question is not in English, translate the question to English before generating the search query.
If you cannot generate a search query, return just the number 0.
"""
    query_prompt_few_shots = [
        {"role": USER, "content": "What are my health plans?"},
        {"role": ASSISTANT, "content": "Show available health plans"},
        {"role": USER, "content": "does my plan cover cardio?"},
        {"role": ASSISTANT, "content": "Health plan cardio coverage"},
    ]

    def __init__(
        self,
        search_client: SearchClient,
        openai_host: str,
        chatgpt_deployment: Optional[str],  # Not needed for non-Azure OpenAI
        chatgpt_model: str,
        embedding_deployment: Optional[str],  # Not needed for non-Azure OpenAI or for retrieval_mode="text"
        embedding_model: str,
        sourcepage_field: str,
        content_field: str,
        query_language: str,
        query_speller: str,
    ):
        self.search_client = search_client
        self.openai_host = openai_host
        self.chatgpt_deployment = chatgpt_deployment
        self.chatgpt_model = chatgpt_model
        self.embedding_deployment = embedding_deployment
        self.embedding_model = embedding_model
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.query_language = query_language
        self.query_speller = query_speller
        self.chatgpt_token_limit = get_token_limit(chatgpt_model)

    async def run_until_final_call(
        self,
        history: list[dict[str, str]],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        should_stream: bool = False,
    ) -> tuple:
        has_text = overrides.get("retrieval_mode") in ["text", "hybrid", None]
        has_vector = overrides.get("retrieval_mode") in ["vectors", "hybrid", None]
        use_semantic_captions = True if overrides.get("semantic_captions") and has_text else False
        top = overrides.get("top", 3)
        filter = self.build_filter(overrides, auth_claims)

        original_user_query = history[-1]["content"]
        user_query_request = "Generate search query for: " + original_user_query

        functions = [
            {
                "name": "search_sources",
                "description": "Retrieve sources from the Azure Cognitive Search index",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_query": {
                            "type": "string",
                            "description": "Query string to retrieve documents from azure search eg: 'Health care plan'",
                        }
                    },
                    "required": ["search_query"],
                },
            }
        ]

        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
        messages = self.get_messages_from_history(
            system_prompt=self.query_prompt_template,
            model_id=self.chatgpt_model,
            history=history,
            user_content=user_query_request,
            max_tokens=self.chatgpt_token_limit - len(user_query_request),
            few_shots=self.query_prompt_few_shots,
        )

        chatgpt_args = {"deployment_id": self.chatgpt_deployment} if self.openai_host == "azure" else {}
        chat_completion = await openai.ChatCompletion.acreate(
            **chatgpt_args,
            model=self.chatgpt_model,
            messages=messages,
            temperature=0.0,
            max_tokens=100,  # Setting too low risks malformed JSON, setting too high may affect performance
            n=1,
            functions=functions,
            function_call="auto",
        )

        query_text = self.get_search_query(chat_completion, original_user_query)

        # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query

        if use_RAG:
        # If retrieval mode includes vectors, compute an embedding for the query
            if has_vector:
                embedding_args = {"deployment_id": self.embedding_deployment} if self.openai_host == "azure" else {}
                embedding = await openai.Embedding.acreate(**embedding_args, model=self.embedding_model, input=query_text)
                query_vector = embedding["data"][0]["embedding"]
            else:
                query_vector = None

            # Only keep the text query if the retrieval mode uses text, otherwise drop it
            if not has_text:
                query_text = None

            # Use semantic L2 reranker if requested and if retrieval mode is text or hybrid (vectors + text)
            if overrides.get("semantic_ranker") and has_text:
                r = await self.search_client.search(
                    query_text,
                    filter=filter,
                    query_type=QueryType.SEMANTIC,
                    query_language=self.query_language,
                    query_speller=self.query_speller,
                    semantic_configuration_name="default",
                    top=top,
                    query_caption="extractive|highlight-false" if use_semantic_captions else None,
                    vector=query_vector,
                    top_k=50 if query_vector else None,
                    vector_fields="embedding" if query_vector else None,
                )
            else:
                r = await self.search_client.search(
                    query_text,
                    filter=filter,
                    top=top,
                    vector=query_vector,
                    top_k=50 if query_vector else None,
                    vector_fields="embedding" if query_vector else None,
                )
            if use_semantic_captions:
                results = [
                    doc[self.sourcepage_field] + ": " + nonewlines(" . ".join([c.text for c in doc["@search.captions"]]))
                    async for doc in r
                ]
            else:
                results = [doc[self.sourcepage_field] + ": " + nonewlines(doc[self.content_field]) async for doc in r]
            content = "\n".join(results)

        # Use semantic L2 reranker if requested and if retrieval mode is text or hybrid (vectors + text)
        content = ""
        results = []
        if os.environ["SHOULD_RAG"] == 'True':
        
            if overrides.get("semantic_ranker") and has_text:
                r = await self.search_client.search(
                    query_text,
                    filter=filter,
                    query_type=QueryType.SEMANTIC,
                    query_language=self.query_language,
                    query_speller=self.query_speller,
                    semantic_configuration_name="default",
                    top=top,
                    query_caption="extractive|highlight-false" if use_semantic_captions else None,
                    vector=query_vector,
                    top_k=50 if query_vector else None,
                    vector_fields="embedding" if query_vector else None,
                )
            else:
                r = await self.search_client.search(
                    query_text,
                    filter=filter,
                    top=top,
                    vector=query_vector,
                    top_k=50 if query_vector else None,
                    vector_fields="embedding" if query_vector else None,
                )
            if use_semantic_captions:
                results = [
                    doc[self.sourcepage_field] + ": " + nonewlines(" . ".join([c.text for c in doc["@search.captions"]]))
                    async for doc in r
                ]
            else:
                results = [doc[self.sourcepage_field] + ": " + nonewlines(doc[self.content_field]) async for doc in r]
                content = "\n".join(results)
            
        follow_up_questions_prompt = (
            self.follow_up_questions_prompt_content if overrides.get("suggest_followup_questions") else ""
        )

        # STEP 3: Generate a contextual and content specific answer using the search results and chat history

        # Allow client to replace the entire prompt, or to inject into the exiting prompt using >>>
        prompt_override = overrides.get("prompt_template")
        if prompt_override is None:
            system_message = self.system_message_chat_conversation.format(
                injected_prompt="", follow_up_questions_prompt=follow_up_questions_prompt
            )
        elif prompt_override.startswith(">>>"):
            system_message = self.system_message_chat_conversation.format(
                injected_prompt=prompt_override[3:] + "\n", follow_up_questions_prompt=follow_up_questions_prompt
            )
        else:
            system_message = prompt_override.format(follow_up_questions_prompt=follow_up_questions_prompt)

        response_token_limit = 1024
        messages_token_limit = self.chatgpt_token_limit - response_token_limit
        messages = self.get_messages_from_history(
            system_prompt=system_message,
            model_id=self.chatgpt_model,
            history=history,
            # Model does not handle lengthy system messages well. Moving sources to latest user conversation to solve follow up questions prompt.
            user_content=original_user_query + "\n\nSources:\n" + content,
            max_tokens=messages_token_limit,
        )
        msg_to_display = "\n\n".join([str(message) for message in messages])

        extra_info = {
            "data_points": results,
            "thoughts": f"Searched for:<br>{query_text}<br><br>Conversations:<br>"
            + msg_to_display.replace("\n", "<br>"),
        }

        chat_coroutine = openai.ChatCompletion.acreate(
            **chatgpt_args,
            model=self.chatgpt_model,
            messages=messages,
            temperature=overrides.get("temperature") or 0.7,
            max_tokens=response_token_limit,
            n=1,
            stream=should_stream,
        )
        return (extra_info, chat_coroutine)

    async def run_without_streaming(
        self,
        history: list[dict[str, str]],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        session_state: Any = None,
    ) -> dict[str, Any]:
        extra_info, chat_coroutine = await self.run_until_final_call(
            history, overrides, auth_claims, should_stream=False
        )
        chat_resp = dict(await chat_coroutine)
        chat_resp["choices"][0]["context"] = extra_info
        chat_resp["choices"][0]["session_state"] = session_state
        return chat_resp

    async def run_with_streaming(
        self,
        history: list[dict[str, str]],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        session_state: Any = None,
    ) -> AsyncGenerator[dict, None]:
        extra_info, chat_coroutine = await self.run_until_final_call(
            history, overrides, auth_claims, should_stream=True
        )
        yield {
            "choices": [
                {
                    "delta": {"role": self.ASSISTANT},
                    "context": extra_info,
                    "session_state": session_state,
                    "finish_reason": None,
                    "index": 0,
                }
            ],
            "object": "chat.completion.chunk",
        }

        async for event in await chat_coroutine:
            # "2023-07-01-preview" API version has a bug where first response has empty choices
            if event["choices"]:
                yield event

    async def run(
        self, messages: list[dict], stream: bool = False, session_state: Any = None, context: dict[str, Any] = {}
    ) -> Union[dict[str, Any], AsyncGenerator[dict[str, Any], None]]:
        overrides = context.get("overrides", {})
        auth_claims = context.get("auth_claims", {})
        if stream is False:
            # Workaround for: https://github.com/openai/openai-python/issues/371
            async with aiohttp.ClientSession() as s:
                openai.aiosession.set(s)
                response = await self.run_without_streaming(messages, overrides, auth_claims, session_state)
            return response
        else:
            return self.run_with_streaming(messages, overrides, auth_claims, session_state)

    def get_messages_from_history(
        self,
        system_prompt: str,
        model_id: str,
        history: list[dict[str, str]],
        user_content: str,
        max_tokens: int,
        few_shots=[],
    ) -> list:
        message_builder = MessageBuilder(system_prompt, model_id)

        # Add examples to show the chat what responses we want. It will try to mimic any responses and make sure they match the rules laid out in the system message.
        for shot in few_shots:
            message_builder.append_message(shot.get("role"), shot.get("content"))

        append_index = len(few_shots) + 1

        message_builder.append_message(self.USER, user_content, index=append_index)
        total_token_count = message_builder.count_tokens_for_message(message_builder.messages[-1])

        newest_to_oldest = list(reversed(history[:-1]))
        for message in newest_to_oldest:
            potential_message_count = message_builder.count_tokens_for_message(message)
            if (total_token_count + potential_message_count) > max_tokens:
                logging.debug("Reached max tokens of %d, history will be truncated", max_tokens)
                break
            message_builder.append_message(message["role"], message["content"], index=append_index)
            total_token_count += potential_message_count
        return message_builder.messages

    def get_search_query(self, chat_completion: dict[str, Any], user_query: str):
        response_message = chat_completion["choices"][0]["message"]
        if function_call := response_message.get("function_call"):
            if function_call["name"] == "search_sources":
                arg = json.loads(function_call["arguments"])
                search_query = arg.get("search_query", self.NO_RESPONSE)
                if search_query != self.NO_RESPONSE:
                    return search_query
        elif query_text := response_message.get("content"):
            if query_text.strip() != self.NO_RESPONSE:
                return query_text
        return user_query
