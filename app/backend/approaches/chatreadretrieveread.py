import os
import json
import logging
import re
from typing import Any, AsyncGenerator, Optional, Union

import aiohttp
import openai
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import QueryType

from approaches.approach import Approach
from core.messagebuilder import MessageBuilder
from core.modelhelper import get_token_limit
from text import nonewlines


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
#     system_message_chat_conversation = """Assistant helps the frontline negotiator with constructing island of agreement table, and questions about the frontline negotiation handbook. Be brief in your answers.
# Incorporate the facts from the handbook and careful reasoning. If there isn't enough information below, say you don't know. If asking a clarifying question to the user would help, ask the question.
# For tabular information return it as an html table. Do not return markdown format. If the question is not in English, answer in the language used in the question.
# Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brackets to reference the source, for example [info1.txt]. Don't combine sources, list each source separately, for example [info1.txt][info2.pdf].
# {follow_up_questions_prompt}
# {injected_prompt}
# """
    system_message_chat_conversation = """Assistant helps the frontline negotiator with constructing island of agreement table, and questions about the frontline negotiation handbook. Be brief in your answers.
Incorporate the facts from the handbook and careful reasoning. If there isn't enough information below, say you don't know. If asking a clarifying question to the user would help, ask the question.
For tabular information return it as an html table. Do not return markdown format. If the question is not in English, answer in the language used in the question.
Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brackets to reference the source, for example [info1.txt]. Don't combine sources, list each source separately, for example [info1.txt][info2.pdf].

An "Island of Agreement Table" is a visual representation used in negotiation processes to identify areas where different parties involved in a negotiation share common ground or agreement. It helps to highlight points of consensus amidst contested issues. The table typically includes four columns:
Contested Facts: This column outlines the facts or points that are disputed or disagreed upon by the parties involved in the negotiation. These are areas where there is a lack of consensus or differing perspectives.
Agreed Facts: This column lists the facts or points that are unanimously accepted or acknowledged by all parties involved. These are areas where there is a shared understanding and agreement.
Convergent Norms: This column highlights the norms, values, or expectations that are shared or aligned among the parties. These are areas where there is common ground in terms of what is considered acceptable or desirable.
Divergent Norms: This column addresses the norms, values, or expectations that differ among the parties. These are areas where there are contrasting views on how things should be done or what is considered appropriate.

Here's a sample negotiation case with its Island of Agreement Table for you to learn about how to generate the island of agreement table. You don't need to analyze this example for me, instead I will provide you the background information and addition information for the a different frontline negotiation case. It's your job to wait until I provide all the information to generate good quality island of agreement and answer the questions.

---------------------------------------------
Background Information:
FWB is an international humanitarian organization dedicated to providing food assistance to populations affected by crises worldwide. Operating in over 70 countries, FWB's overarching mission is to save lives and restore human dignity through the provision of food aid. FWB is planning the distribution of urgently needed food aid within a refugee camp situated in Country Alpha. 
The UN Humanitarian Coordinator in Alpha has issued a press release expressing profound concern for the plight of over 160,000 forcibly displaced refugees, a consequence of acute violence in Omega, a neighboring country, over the past few months. According to the statement, these refugees have settled in multiple camps in proximity to the capital. The camps are receiving a continuous influx of new arrivals, with reports from local church activists highlighting a majority of newcomers as children and women facing severe nutritional deficiencies, along with inadequate shelter and access to clean water. The overall sanitary and hygiene conditions within the camps are dire, with healthcare services being limited to mobile clinics operated by an NGO called Health for All. Insights from contacts within the refugee population indicate that the displaced individuals are confined to the camps under the watch of local guards and require official permission to leave.
The primary camp, housing over 160,000 displaced individuals, is located near the National Hero Roundabout, approximately 35 km north of the capital. This camp is overseen by local authorities with established links to armed militias actively participating in hostilities against Omega's government. These militias have been implicated in targeting civilian populations in Omega and attacking refugees originating from Omega. MASHA, a local NGO, has reported that a significant portion of the primary camp's security guards are members of the armed militia, and they have been observed imposing stringent controls over the camp's population, occasionally engaging in extortion and violence against the most vulnerable refugees.
FWB has offered to provide emergency food rations to the recently arrived refugee families, and the camp authorities have agreed to accept FWB's food aid. However, the camp authorities are requiring that FWB hires local guards to assist in the food ration distribution process. The camp authorities argue that the guards' duties during food distribution extend beyond their security roles and should be compensated similarly to other day laborers. Importantly, the camp authorities will not permit anyone else to work on behalf of FWB within the camp.
Additionally, the camp authorities anticipate that the local guards should receive compensation in the form of food rations for their services. They argue that the families of these guards are also grappling with food insecurity, and cash payments hold limited utility in the region due to exorbitant local market food prices. Food rations are increasingly becoming the sole acceptable means of compensation. However, this request contradicts FWB's policies about in-kind food payments due to concerns about the risk of the food aid being diverted from its intended beneficiaries to be resold at market price. In response, the Camp Commander has noted that many refugees are already trading their rations on the camp's market in exchange for phone SIM cards.
As a humanitarian organization, FWB is steadfast in its commitment to providing emergency food aid to the refugee population as swiftly and impartially as possible. FWB representatives are deeply apprehensive that entrusting local guards with the food distribution could potentially lead to further exploitation of the refugees. The demands set forth by the camp authorities appear to be at odds with FWB's core principles of neutrality, impartiality, and independence.
The local team of FWB is now tasked with devising a negotiation strategy to engage with the camp authorities. The objective of this negotiation with the Camp Commander is to secure its presence and establish the terms of operation within the refugee camp, aiming for optimal food distribution results while minimizing any adverse impact on FWB as an organization and the refugee population as beneficiaries. In the absence of a prompt agreement, the lives of thousands of refugees will be at risk.

Additional Information:
1.	Source: UN report: 
According to the UN Humanitarian Coordinator, large numbers of newly arrived refugees are facing food shortages. The number of refugees is increasing day by day. There are now over 160,000 people in the camp near the National Hero Roundabout.

2.	Source: Minutes of Meeting (MoM) with the Camp Commander: 
FWB seeks to identify refugees experiencing food insecurity; however, the camp figures are outdated. FWB intends to conduct a nutritional assessment, which may take approximately one week due to the population’s size. This assessment is crucial before initiating food distribution, as it aligns with the German government's stipulation. The German government, a significant donor to FWB, insists on a comprehensive nutritional assessment to ensure food aid goes to those truly in need, rather than being diverted by local armed militias.
In the meeting, the Camp Commander asserted that existing data collected by the Camp Administration regarding the population's nutritional status is sufficient. He deems a new technical assessment unnecessary and requires FWB proceed swiftly with a three-month food ration distribution to alleviate pressure on refugee families.

3.	Source: MoM with MASHA, a local charitable organization: 
According to early findings gathered by MASHA within the camp, a majority of refugees are in dire need of food assistance. There are concerns of aid diversion due to the camp guards' affiliation with the local militia, known to exploit camp residents. Instances of violence and threats by guards against refugees who refuse to provide money or food rations have been documented. The guards exercise significant control over the camp and its population.	
MASHA reports that refugees are essentially confined to the camp, requiring authorization from camp authorities to leave. They are unable to seek employment outside the camp and depend entirely on humanitarian food assistance. Some refugees resort to selling their food rations to obtain phone SIM cards and other necessities from local merchants, who, in turn, sell the rations in the villages and nearby communities surrounding the camp.
MASHA informs FWB that there is growing pressure on the Camp Commander to secure renewed food assistance, as camp stores are nearly depleted. Without an immediate influx of food rations from humanitarian organizations, the Camp Commander lacks the resources to pay the guards. Moreover, without food supplies, the refugee population may attempt to leave the camp at the National Hero Roundabout, heading closer to the capital. This would be disastrous for the Camp Commander, the local militia, and the village that relies on camp-related activities. The camp was strategically established to prevent refugees from settling in the vicinity of the capital.

4.	Source: MoM with Camp Commander: 
The Camp Commander acknowledges the need for relief assistance to reach refugees but emphasizes the importance of a clear distribution plan. He insists that guards must always accompany FWB representatives within the camp due to security concerns. However, FWB, based on its principles of neutrality, impartiality, and independence, requests the freedom for its staff to move within the camp and engage with refugees without guard presence. This request does not sit well with the Camp Commander.

5.	Source: MoM with the Camp Administrator: 
The Camp Administrator estimates that FWB will require 200 daily laborers for food ration distribution within the camp. A list of potential hires, predominantly consisting of guards and their family members from the local community, has been provided. FWB accepts the list but asserts that all names must undergo vetting by FWB administration. The organization does not intend to hire guards or their relatives, citing concerns about aid diversion and maintaining neutrality. Ideally, FWB wishes to employ individuals from the local community surrounding the camp. FWB commits to contacting the local mayor to explore recruitment options for 200 daily laborers. Although acknowledging the importance of involving the local community, the Camp Administrator appears displeased with this plan.

6.	Source: MoM with the Camp Commander: 
Camp Authorities has informed FWB that it does not allow FWB to hire anybody else but guards. FWB informs the Camp authorities that it cannot hire guards because they are members of the local militia – that is party to the conflict. To hire the guards would be a violation to the rules of neutrality and independence of FWB.

7.	Source: MoM with the Mayor of the local village: 
The Mayor informs FWB that while food insecurity prevails in the region, there is no severe hunger. The local economy heavily relies on job opportunities within the camp. Many young men are part of the local militia, and their families benefit when their sons serve in this capacity. Upon their return from fighting on the frontlines, their benefits may include employment as guards at the camp, with compensation in the form of food rations.
The Mayor confirms that there are very few consumer goods available in the market, so most payment to the staff of the camp take place in the form of food rations that are then sold or exchanged for other necessities at the market of the village. One can see the logos of humanitarian organizations in the packaging of the goods sold at the market. The Mayor believes that FWB will probably need to pay its daily laborer in food rations as there in not much to buy with money at the market. FWB explains to the Mayor that it prefers to pay its employees and daily laborers in cash to avoid encouraging the diversion of food assistance from the refugees. According to the principles of FWB and agreements with the donors, all the FWB food should go to the refugees. The Mayor recommends to FWB to find a practical solution to the issue of hiring and compensating local guards. It is most unlikely that the Camp Commander would allow other people to work in the camp as the guards depend on the food provided by international NGOs to feed their families.

8.	Source: MoM with the Minister of Defense of Alpha
In a tense meeting between FWB representatives and the Minister of Defense of Alpha, it became apparent that the Alpha government views all refugees from Omega as potential terrorists infiltrating its territory. Alpha mandates strict regulation of these individuals within camps. Alpha perceives FWB's role as supporting the government of Alpha and the Camp Administration. Furthermore, Alpha does not consider them as “refugees” in a legal sense and is ready to deport anyone who does not comply with the laws of Alpha.

9.	Source: Press Statement of the Council of Omega Abroad
The Council expresses concern over the influx of refugees from Omega into Alpha. It condemns the violence against Omega's refugees, perpetrated by the government and its affiliated "terror brigades." The Council calls on the international community to provide urgent assistance and protection to these refugees in Alpha. The Council encourages refugees to leave Alpha, which it does not consider a safe haven for Omega's people.

10.	Source: MoM with Health for All
During a meeting between FWB representatives and Health for All, an NGO operating mobile clinics in the camp, Health for All expresses deep concern for the well-being and dignity of the camp's population. Numerous threats, including disease, malnutrition, and violence, endanger refugees. Health for All urges FWB to adopt a pragmatic approach to operate effectively within the camp. Health for All discloses that it has been working with and compensating guards around mobile clinics as a strategy to manage the population accessing healthcare. Furthermore, it offers free medical services to guards since many of the them have suffered injuries on the frontlines.

11.	Source: Local press
Local press reports have taken a critical stance toward refugees, emphasizing the continuous influx of refugees and a rise in crimes around the camps. The press supports the government's efforts to confine refugees within camps where they can receive assistance. It calls on the international community to provide equitable aid to the local communities surrounding the camps, which have also suffered due to the conflict and regional tensions.

12.	Source: MoM with local church activists
Local church activists express growing concerns about the increasing influence of former militia members and their families in the community. They perceive these ex-fighters from the frontlines as introducing negative behaviors and endorsing abusive practices. They highlight refugees as the primary victims of these abuses within the camps. Local community members have also fallen victim to abuses by former militia members. Local church activists support FWB's decision to refrain from further empowering militia members and local guards by hiring them and compensating them with food rations.

13.	Source: MoM with the leaders of the Militia
In an unexpected meeting between FWB representatives and militia leaders, the leaders express their frustration with what they perceive as FWB's discrimination against local guards, who they believe deserve food assistance just as much as anyone else. These guards have served their country and are deemed more deserving of aid than refugees who have merely fled conflict. The militia leaders indicate their intent to closely monitor FWB, considering it a source of support for numerous spies and infiltrators within the camp. These individuals are not refugees but rather viewed as terrorists.

14.	Source: MoM with the leaders of the local guards
Leaders of the local guards visit FWB's camp office and present a list of urgently needed food items for themselves and their families. They emphasize that they will not authorize their members to work in the camp unless their requested assistance is provided.

15.	Source: MoM with refugee leaders
Refugee leaders within the camp meet with FWB's camp office head. They express frustration with the international community's perceived inaction regarding their situation. They feel trapped by the local guards and militia and call upon the world to intervene and free them from ongoing suffering, particularly women and children. They strongly oppose the idea of local guards overseeing humanitarian food distribution, given the abuses they've endured at the hands of the militia. Refugee leaders are critical of FWB and other charitable organizations for their perceived lack of accountability toward camp beneficiaries.


Here is an example of an Island of Agreement Table generated based on the above information:

Contest Facts:
1. Need for a new nutritional assessment.
2. FWB's apprehension about local guards' role in distribution.
3. Exact number of refugees experiencing food insecurity.
4. FWB's insistence on conducting an independent assessment versus reliance on existing camp data.
5. Validity and reliability of data from various sources like MASHA and the UN report.

Agreed Facts:
1. Over 160,000 refugees in the camp.
2. Continuous influx of refugees.
3. Camp located near the National Hero Roundabout.
4. Reports of refugees trading rations for phone SIM cards.
5. Refugees are confined to the camp and reply heavily on humanitarian aid.

Convergent Norms:
1. Food assistance is critically required for refugees.
2. The primary objective is to save lives by ensuring food aid reaches the most vulnerable.
3. Both FWB and Camp Commander aim to support the well-being of the refugees.
4. Need for a systematic and efficient food distribution process.
5. Both parties acknowledge the risk of food diversion and aim to prevent it.

Divergent Norms:
1. In-kind food payment to local guards.
2. FWB's policies versus local practices about compensation.
3. Acceptance of FWB's core principles by camp authorities.
4. Role and allegiance of local guards within the camp.
5. The balance between speed of distribution and thorough assessment.
---------------------------------------------"""
    
    follow_up_questions_prompt_content = """Generate 3 very brief follow-up questions that the user would likely ask next.
Enclose the follow-up questions in double angle brackets. Example:
<<Are there exclusions for prescriptions?>>
<<Which pharmacies can be ordered from?>>
<<What is the limit for over-the-counter medication?>>
Do no repeat questions that have already been asked.
Make sure the last question ends with ">>"."""

    query_prompt_template = """Below is a history of the conversation so far, and a new question asked by the user that needs to be answered by searching in a knowledge base about frontline negotitation handbook, reasoning about political tention and evaluating norms and facts.
You have access to Azure Cognitive Search index with 100's of documents.
Generate a search query based on the conversation and the new question.
Do not include cited source filenames and document names e.g info.txt or doc.pdf in the search query terms.
Do not include any text inside [] or <<>> in the search query terms.
Do not include any special characters like '+'.
If the question is not in English, translate the question to English before generating the search query.
If you cannot generate a search query, return just the number 0.
"""
    query_prompt_few_shots = [
        {"role": USER, "content": "What is frontline negotiation?"},
        {"role": ASSISTANT, "content": "Describe frontline negotiation"},
        {"role": USER, "content": "what is frontline negotiation?"},
        {"role": ASSISTANT, "content": "Frontline Negotiation"},
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
        # TODO: Fall back to the raw text instead of parsing file, need to figure out import paths.
        # print(os.getcwd())
        # with open('./system.txt', 'r') as file:
        #     self.system_message_chat_conversation = file.read()
        

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
        if overrides.get("suggest_followup_questions"):
            content, followup_questions = self.extract_followup_questions(chat_resp["choices"][0]["message"]["content"])
            chat_resp["choices"][0]["message"]["content"] = content
            chat_resp["choices"][0]["context"]["followup_questions"] = followup_questions
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

        followup_questions_started = False
        followup_content = ""
        async for event in await chat_coroutine:
            # "2023-07-01-preview" API version has a bug where first response has empty choices
            if event["choices"]:
                # if event contains << and not >>, it is start of follow-up question, truncate
                content = event["choices"][0]["delta"].get("content", "")
                if overrides.get("suggest_followup_questions") and "<<" in content:
                    followup_questions_started = True
                    earlier_content = content[: content.index("<<")]
                    if earlier_content:
                        event["choices"][0]["delta"]["content"] = earlier_content
                        yield event
                    followup_content += content[content.index("<<") :]
                elif followup_questions_started:
                    followup_content += content
                else:
                    yield event
        if followup_content:
            _, followup_questions = self.extract_followup_questions(followup_content)
            yield {
                "choices": [
                    {
                        "delta": {"role": self.ASSISTANT},
                        "context": {"followup_questions": followup_questions},
                        "finish_reason": None,
                        "index": 0,
                    }
                ],
                "object": "chat.completion.chunk",
            }

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
        for shot in reversed(few_shots):
            message_builder.insert_message(shot.get("role"), shot.get("content"))

        append_index = len(few_shots) + 1

        message_builder.insert_message(self.USER, user_content, index=append_index)
        total_token_count = message_builder.count_tokens_for_message(message_builder.messages[-1])

        newest_to_oldest = list(reversed(history[:-1]))
        for message in newest_to_oldest:
            potential_message_count = message_builder.count_tokens_for_message(message)
            if (total_token_count + potential_message_count) > max_tokens:
                logging.debug("Reached max tokens of %d, history will be truncated", max_tokens)
                break
            message_builder.insert_message(message["role"], message["content"], index=append_index)
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

    def extract_followup_questions(self, content: str):
        return content.split("<<")[0], re.findall(r"<<([^>>]+)>>", content)
