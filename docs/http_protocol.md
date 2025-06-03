# RAG Chat: HTTP Protocol

The frontend and backend of this RAG chat application exchange messages over HTTP, using both regular JSON for single responses and streaming newline-delimited JSON (NDJSON) for streamed responses.

The HTTP protocol is inspired by the [OpenAI ChatCompletion API](https://platform.openai.com/docs/guides/text-generation/chat-completions-api), but contains additional fields required for the chat application.

Table of contents:

* [HTTP requests to chat app endpoints](#http-requests-to-chat-app-endpoints)
  * [Request context properties](#request-context-properties)
* [HTTP responses from RAG chat app endpoints](#http-responses-from-rag-chat-app-endpoints)
  * [Non-streaming response](#non-streaming-response)
    * [Successful response](#successful-response)
    * [Error response](#error-response)
  * [Streaming response](#streaming-response)
    * [Successful streamed response](#successful-streamed-response)
    * [Error in streamed response](#error-in-streamed-response)
  * [Answer formatting](#answer-formatting)
  * [Response context properties](#response-context-properties)

## HTTP requests to chat app endpoints

All requests use the POST method, with the following headers:

* `Content-Type: application/json`
* `Authorization: Bearer <ID token>`: _Optional._ For authentication, if the app is deployed with [user login enabled](./login_and_acl.md)

The path is `chat` for a non-streaming request and `chat/stream` for a streaming request.

The body of the request contains these properties, in JSON format:

* `"messages"`: A list of messages, each containing "content" and "role", where "role" may be "assistant" or "user". When triggered from the "Ask" tab (single-turn RAG), the list will contain a single message, whereas requests from the "Chat" tab (multi-turn RAG) may contain multiple messages.
* `"session_state"`: _Optional_. An object containing the "memory" for the chat app, such as the session ID for chat history storage.
* `"context"`: _Optional_. An object containing any additional options for the request, such as the `temperature` to use for the LLM. See below for supported options.

### Usage example

The example belows represents a valid and compliant request body to the chat app endpoints:

```json
{
    "messages": [
        {
            "content": "What is included in my Northwind Health Plus plan that is not in standard?",
            "role": "user"
        }
    ],
    "context": {},
    "session_state": null
}
```

### Request context properties

These are the currently supported properties in the `context` object:

* `"overrides"`: An object containing settings for the chat application.
  * `"temperature"`: The temperature to use for the LLM for the question-answering chat completion call.
  * `"top"`: The number of results to return from Azure AI Search.
  * `"retrieval_mode"`: The mode to use for the Azure AI Search step. Can be "hybrid", "vectors", or "text".
  * `"semantic_ranker"`: Whether to use the semantic ranker for the Azure AI Search step.
  * `"semantic_captions"`: Whether to use semantic captions for the Azure AI Search step.
  * `"suggest_followup_questions"`: Whether to suggest follow-up questions for the chat app.
  * `"use_oid_security_filter"`: Whether to use the OID security filter for the Azure AI Search step.
  * `"use_groups_security_filter"`: Whether to use the groups security filter for the Azure AI Search step.
  * `"vector_fields"`: A list of fields to search for the Azure AI Search step.
  * `"use_gpt4v"`: Whether to use a GPT-4V approach.
  * `"gpt4v_input"`: The input type to use for a GPT-4V approach. Can be "text", "textAndImages", or "images".

Example of the overrides object:

```json
"overrides": {
    "top": 3,
    "retrieval_mode": "text",
    "semantic_ranker": false,
    "semantic_captions": false,
    "suggest_followup_questions": false,
    "use_oid_security_filter": false,
    "use_groups_security_filter": false,
    "vector_fields": ["embedding"],
    "use_gpt4v": false,
    "gpt4v_input": "textAndImages"
}
```

## HTTP responses from RAG chat app endpoints

The HTTP response is JSON for a non-streaming response, or [newline-delimited JSON](https://ndjson.org/home/) ("NDJSON"/"jsonlines") for a streaming response.

### Non-streaming response

The response contains this header:

* `Content-Type: application/json`

#### Successful response

A successful response has a status code of 200, and the body contains a JSON object with the following properties:

* `"message"`: An object containing the actual content of the response.  See [Answer formatting](#answer-formatting). _Comes from the [OpenAI chat completion object](https://platform.openai.com/docs/api-reference/chat/object)._
* `"session_state"`: _Optional_. An object containing the "memory" for the chat app, such as the session ID for chat history storage.
* `"context"`: _Optional_. An object containing additional details needed for the chat app, used for citation display and the thought process tab. See [response context properties](#response-context-properties).

Here's an example JSON response:

```json
{
    "message": {
        "content": "There is no specific information provided about what is included in the Northwind Health Plus plan that is not in the standard plan. It is recommended to read the plan details carefully and ask questions to understand the specific benefits of the Northwind Health Plus plan [Northwind_Standard_Benefits_Details.pdf#page=91].",
        "function_call": null,
        "role": "assistant",
        "tool_calls": null
    },
    "context": {
        "data_points": {
            "text": [
                "Northwind_Standard_Benefits_Details.pdf#page=91:    Tips for Avoiding Intentionally False Or Misleading Statements:   When it comes to understanding a health plan, it is important to be aware of any  intentiona lly false or misleading statements that the plan provider may make...(truncated)",
                "Northwind_Standard_Benefits_Details.pdf#page=91:  It is important to  research the providers and services offered in the Northwind Standard plan in order to  determine if the providers and services offered are sufficient for the employee's needs...(truncated)",
                "Northwind_Standard_Benefits_Details.pdf#page=17:  Employees should keep track of their claims and follow up with  Northwind Health if a claim is not processed in a timely manner...(truncated)"
            ]
        },
        "thoughts": [
            {
                "description": "What is included in my Northwind Health Plus plan that is not in standard?",
                "props": null,
                "title": "Original user query"
            },
            {
                "description": "Northwind Health Plus plan coverage details compared to standard plan",
                "props": {
                    "has_vector": false,
                    "use_semantic_captions": false
                },
                "title": "Generated search query"
            },
            {
                "description": [
                    {
                        "captions": [],
                        "category": null,
                        "content": "  \nTips for Avoiding Intentionally False Or Misleading Statements:  \nWhen it comes to understanding a health plan, it is important to be aware of any \nintentiona lly false or misleading statements that the plan provider may make...(truncated)",
                        "embedding": null,
                        "groups": [],
                        "id": "file-Northwind_Standard_Benefits_Details_pdf-4E6F72746877696E645F5374616E646172645F42656E65666974735F44657461696C732E706466-page-233",
                        "imageEmbedding": null,
                        "oids": [],
                        "sourcefile": "Northwind_Standard_Benefits_Details.pdf",
                        "sourcepage": "Northwind_Standard_Benefits_Details.pdf#page=91"
                    },
                    {
                        "captions": [],
                        "category": null,
                        "content": " It is important to \nresearch the providers and services offered in the Northwind Standard plan i n order to \ndetermine if the providers and services offered are sufficient for the employee's needs...(truncated)",
                        "embedding": null,
                        "groups": [],
                        "id": "file-Northwind_Standard_Benefits_Details_pdf-4E6F72746877696E645F5374616E646172645F42656E65666974735F44657461696C732E706466-page-232",
                        "imageEmbedding": null,
                        "oids": [],
                        "sourcefile": "Northwind_Standard_Benefits_Details.pdf",
                        "sourcepage": "Northwind_Standard_Benefits_Details.pdf#page=91"
                    },
                    {
                        "captions": [],
                        "category": null,
                        "content": " Employees should keep track of their claims and follow up with \nNorthwind Health if a claim is not processed in a timely manner...(truncated)",
                        "embedding": null,
                        "groups": [],
                        "id": "file-Northwind_Standard_Benefits_Details_pdf-4E6F72746877696E645F5374616E646172645F42656E65666974735F44657461696C732E706466-page-41",
                        "imageEmbedding": null,
                        "oids": [],
                        "sourcefile": "Northwind_Standard_Benefits_Details.pdf",
                        "sourcepage": "Northwind_Standard_Benefits_Details.pdf#page=17"
                    }
                ],
                "props": null,
                "title": "Results"
            },
            {
                "description": [
                    "{'role': 'system', 'content': \"Assistant helps the company employees with their healthcare plan questions, and questions about the employee handbook. Be brief in your answers.\n        Answer ONLY with the facts listed in the list of sources below. If there isn't enough information below, say you don't know. Do not generate answers that don't use the sources below. If asking a clarifying question to the user would help, ask the question.\n        For tabular information return it as an html table. Do not return markdown format. If the question is not in English, answer in the language used in the question.\n        Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brackets to reference the source, for example [info1.txt]. Don't combine sources, list each source separately, for example [info1.txt][info2.pdf].\n        \n        \n        \"}",
                    "{'role': 'user', 'content': \"What is included in my Northwind Health Plus plan that is not in standard?\n\nSources:\nNorthwind_Standard_Benefits_Details.pdf#page=91:    Tips for Avoiding Intentionally False Or Misleading Statements:   When it comes to understanding a health plan, it is important to be aware of any  intentiona lly false or misleading statements that the plan provider may make. To avoid  being misled, employees should follow the following tips:(truncated)
                    \nNorthwind_Standard_Benefits_Details.pdf#page=91:  It is important to  research the providers and services offered in the Northwind Standard plan in order to  determine if the providers and services offered are sufficient for the employee's needs.   In addition, Northwind Health may make claims that their plan offers low or no cost  prescription drugs..(truncated)\"}"
                ],
                "props": null,
                "title": "Prompt"
            }
        ]
    },
    "session_state": null
}
```

#### Error response

An error response has a status code of 400 or 500, and the body contains a JSON object with the following properties:

* `"error"`: A string describing the error.

Here's an example JSON response for a 500-level error:

```json
{
    "error": "The app encountered an error processing your request.\nIf you are an administrator of the app, view the full error in the logs."
}
```

Here's an example JSON response for a 400-level error:

```json
{
    "error": "Your message contains content that was flagged by the OpenAI content filter."
}
```

### Streaming response

The response contains these headers:

* `Content-Type: application/json-lines`
* `Transfer-Encoding: chunked`

#### Successful streamed response

A successful response has a status code of 200.
The body of the response contains a sequence of JSON objects, each representing a chunk of the response.
The first chunk contains the `context` property, since that is available before the answer, and subsequent chunks contain parts of the answer to the question.

Each JSON object contains the following properties:

* `"delta"`: An object containing the actual content of the response, a token at a time. See [Answer formatting](#answer-formatting). _Comes from the [OpenAI chat completion chunk object](https://platform.openai.com/docs/api-reference/chat/streaming)._
* `"context"`: _Optional_. An object containing additional details needed for the chat app. Each application can define its own properties. See [response context properties](#response-context-properties).
* `"session_state"`: _Optional_. An object containing the "memory" for the chat app, such as a user ID.

Here's an example of the first three JSON objects in a streaming response:

```json
{
    "delta": {
        "role": "assistant"
    },
    "context": {
        "data_points": {
            "text": [
                "Benefit_Options.pdf#page=3:  The plans also cover preventive care services such as mammograms, colonoscopies, and  other cancer screenings...(truncated)",
                "Benefit_Options.pdf#page=3:   Both plans offer coverage for medical services. Northwind Health Plus offers coverage for hospital stays,  doctor visits,...(truncated)",
                "Benefit_Options.pdf#page=3:  With Northwind Health Plus, you can choose  from a variety of in -network providers, including primary care physicians,...(truncated)"
            ]
        },
        "thoughts": [
            {
                "title": "Original user query",
                "description": "What is included in my Northwind Health Plus plan that is not in standard?",
                "props": null
            },
            {
                "title": "Generated search query",
                "description": "Northwind Health Plus plan standard",
                "props": {
                    "use_semantic_captions": false,
                    "has_vector": false
                }
            },
            {
                "title": "Results",
                "description": [
                    {
                        "id": "file-Benefit_Options_pdf-42656E656669745F4F7074696F6E732E706466-page-2",
                        "content": " The plans also cover preventive care services such as mammograms, colonoscopies, and \nother cancer screenings...(truncated)",
                        "embedding": null,
                        "imageEmbedding": null,
                        "category": null,
                        "sourcepage": "Benefit_Options.pdf#page=3",
                        "sourcefile": "Benefit_Options.pdf",
                        "oids": [],
                        "groups": [],
                        "captions": []
                    },
                    {
                        "id": "file-Benefit_Options_pdf-42656E656669745F4F7074696F6E732E706466-page-3",
                        "content": " \nBoth plans offer coverage for medical services. Northwind Health Plus offers coverage for hospital stays, \ndoctor visits,...(truncated)",
                        "embedding": null,
                        "imageEmbedding": null,
                        "category": null,
                        "sourcepage": "Benefit_Options.pdf#page=3",
                        "sourcefile": "Benefit_Options.pdf",
                        "oids": [],
                        "groups": [],
                        "captions": []
                    },
                    {
                        "id": "file-Benefit_Options_pdf-42656E656669745F4F7074696F6E732E706466-page-1",
                        "content": " With Northwind Health Plus, you can choose \nfrom a variety of in -network providers, including primary care physicians,...(truncated)",
                        "embedding": null,
                        "imageEmbedding": null,
                        "category": null,
                        "sourcepage": "Benefit_Options.pdf#page=3",
                        "sourcefile": "Benefit_Options.pdf",
                        "oids": [],
                        "groups": [],
                        "captions": []
                    }
                ],
                "props": null
            },
            {
                "title": "Prompt",
                "description": [
                    "{'role': 'system', 'content': \"Assistant helps the company employees with their healthcare plan questions, and questions about the employee handbook. Be brief in your answers.\\n        Answer ONLY with the facts listed in the list of sources below. If there isn't enough information below, say you don't know. Do not generate answers that don't use the sources below. If asking a clarifying question to the user would help, ask the question.\\n        For tabular information return it as an html table. Do not return markdown format. If the question is not in English, answer in the language used in the question.\\n        Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brackets to reference the source, for example [info1.txt]. Don't combine sources, list each source separately, for example [info1.txt][info2.pdf].\\n        \\n        \\n        \"}",
                    "{'role': 'user', 'content': 'What is included in my Northwind Health Plus plan that is not in standard?'}",
                    "{'role': 'assistant', 'content': 'There is no specific information provided about what is included in the Northwind Health Plus plan that is not in the standard plan. It is recommended to read the plan details carefully and ask questions to understand the specific benefits of the Northwind Health Plus plan [Northwind_Standard_Benefits_Details.pdf#page=91].'}",
                    "{'role': 'user', 'content': \"What is included in my Northwind Health Plus plan that is not in standard?\\n\\nSources:\\nBenefit_Options.pdf#page=3:  The plans also cover preventive care services such as mammograms, colonoscopies, and  other cancer screenings...(truncated)\\nBenefit_Options.pdf#page=3:   Both plans offer coverage for medical services. Northwind Health Plus offers coverage for hospital stays,  doctor visits,...(truncated)\\nBenefit_Options.pdf#page=3:  With Northwind Health Plus, you can choose  from a variety of in -network providers, including primary care physicians,...(truncated)\"}"
                ],
                "props": null
            }
        ]
    },
    "session_state": null,
}{
    "delta": {
        "content": null,
        "function_call": null,
        "role": "assistant",
        "tool_calls": null
    }
}{
    "delta": {
        "content": "The",
        "function_call": null,
        "role": null,
        "tool_calls": null
    }
}
```

#### Error in streamed response

If an error is encountered before the stream begins, then the response may look like a non-streaming error response. However, if an error is encountered during the stream, then the server will have already sent a 200 response, and will send a chunk with an error object. Typically that would be the last chunk, but it may not be.

Here's an example of an error chunk:

```json
{
    "error": "The app encountered an error processing your request.\nIf you are an administrator of the app, view the full error in the logs."
}
```

### Answer formatting

To support the display of citations, the answer from the LLM should contain source information in square brackets, such as `[info1.txt]`.

Here's a full example of an answer with citation:

```text
There is no specific information provided about what is included in the Northwind Health Plus plan that is not in the standard plan. It is recommended to read the plan details carefully and ask questions to understand the specific benefits of the Northwind Health Plus plan [Northwind_Standard_Benefits_Details.pdf#page=91].
```

### Response context properties

The response context object can contain the following properties:

* `"followup_questions"`: A list of follow-up questions to ask the user.

    Example:

    ```json
    "followup_questions": [
        "What types of prescription drugs are covered?",
        "Which services have lower out-of-pocket costs?"
    ]
    ```

    When the app sees this property in the response and the user has requested follow-up questions (in the settings), the app prompts the user with clickable versions of the questions. [See image](./images/followup.png)

* `"data_points"`: An object containing text and/or image data chunks, a list in the `"text"` or `"images"` properties.

    Example:

    ```json
    "data_points": {
        "text": [
            "Northwind_Standard_Benefits_Details.pdf#page=91:    Tips for Avoiding Intentionally False Or Misleading Statements:   When it comes to understanding a health plan, it is important to be aware of any intentionally false or misleading statements that the plan provider may make...(truncated)",
            "Northwind_Standard_Benefits_Details.pdf#page=91:  It is important to research the providers and services offered in the Northwind Standard plan in order to  determine if the providers and services offered are sufficient for the employee's needs...(truncated)",
            "Northwind_Standard_Benefits_Details.pdf#page=17:  Employees should keep track of their claims and follow up with  Northwind Health if a claim is not processed in a timely manner...(truncated)"
        ]
    },
    ```

    Example with images:

    ```json
    "data_points": {
        "images": [
            {
                "detail": "auto",
                "url": "data:image/png;base64,iVBOR1BORw0KGgoAAAANSUhEUgAAAAEAAAABAQAAAAA3bvkkAAAACklEQVR4nGMAAQAABQABDQ0tuhsAAAAASUVORK5CYII="
            }
        ],
        "text": [
            "Financial Market Analysis Report 2023-6.png: 3</td><td>1</td></tr></table> Financial markets are interconnected, with movements in one segment often influencing other...(truncated)"
        ]
    },
    ```

    The app turns the data points into clickable citations and the "Supporting content" tab. [See image](./images/data_points.png)

* `"thoughts"`: A list describing each step of the backend. Each step should contain:
  * `"title"`: A string describing the step.
  * `"description"`: A string or list of strings describing the step.
  * `"props"`: _Optional_. An object containing additional properties for the step.

    Example:

    ```json
    "thoughts": [
        {
            "title": "Original user query",
            "description": "What is included in my Northwind Health Plus plan that is not in standard?",
            "props": null
        },
        {
            "title": "Generated search query",
            "description": "Northwind Health Plus plan coverage details",
            "props": {
                "has_vector": false,
                "use_semantic_captions": false
            }
        },
        {
            "title": "Results",
            "description": [
                {
                    "captions": [],
                    "category": null,
                    "content": "  \n\u2022 Understand your coverage limits, and know what services are  covered and what services \nare not covered...(truncated)",
                    "embedding": null,
                    "groups": [],
                    "id": "file-Northwind_Health_Plus_Benefits_Details_pdf-4E6F72746877696E645F4865616C74685F506C75735F42656E65666974735F44657461696C732E706466-page-249",
                    "imageEmbedding": null,
                    "oids": [],
                    "sourcefile": "Northwind_Health_Plus_Benefits_Details.pdf",
                    "sourcepage": "Northwind_Health_Plus_Benefits_Details.pdf#page=100"
                },
                {
                    "captions": [],
                    "category": null,
                    "content": " Employees should keep track of their claims and follow up with \nNorthwind Health if a claim is not processed in a timely manner...(truncated)",
                    "embedding": null,
                    "groups": [],
                    "id": "file-Northwind_Standard_Benefits_Details_pdf-4E6F72746877696E645F5374616E646172645F42656E65666974735F44657461696C732E706466-page-41",
                    "imageEmbedding": null,
                    "oids": [],
                    "sourcefile": "Northwind_Standard_Benefits_Details.pdf",
                    "sourcepage": "Northwind_Standard_Benefits_Details.pdf#page=17"
                },
                {
                    "captions": [],
                    "category": null,
                    "content": " It is important to talk to your doctor or \nhealth care provider to make su re that you understand the details of the clinical trial before \nyou decide to participate...(truncated)",
                    "embedding": null,
                    "groups": [],
                    "id": "file-Northwind_Health_Plus_Benefits_Details_pdf-4E6F72746877696E645F4865616C74685F506C75735F42656E65666974735F44657461696C732E706466-page-57",
                    "imageEmbedding": null,
                    "oids": [],
                    "sourcefile": "Northwind_Health_Plus_Benefits_Details.pdf",
                    "sourcepage": "Northwind_Health_Plus_Benefits_Details.pdf#page=24"
                }
            ],
            "props": null
        },
        {
            "title": "Prompt",
            "description": [
                "{'role': 'system', 'content': 'Assistant helps the company employees with their healthcare plan questions, and questions about the employee handbook. Be brief in your answers.\\n        Answer ONLY with the facts listed in the list of sources below. If there isn\\'t enough information below, say you don\\'t know. Do not generate answers that don\\'t use the sources below. If asking a clarifying question to the user would help, ask the question.\\n        For tabular information return it as an html table. Do not return markdown format. If the question is not in English, answer in the language used in the question.\\n        Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brackets to reference the source, for example [info1.txt]. Don\\'t combine sources, list each source separately, for example [info1.txt][info2.pdf].\\n        Generate 3 very brief follow-up questions that the user would likely ask next.\\n    Enclose the follow-up questions in double angle brackets. Example:\\n    <<Are there exclusions for prescriptions?>>\\n    <<Which pharmacies can be ordered from?>>\\n    <<What is the limit for over-the-counter medication?>>\\n    Do no repeat questions that have already been asked.\\n    Make sure the last question ends with \">>\".\\n    \\n        \\n        '}",
                "{'role': 'user', 'content': 'What is included in my Northwind Health Plus plan that is not in standard?'}",
                "{'role': 'assistant', 'content': 'The Northwind Health Plus plan includes coverage for prescription drugs, but it is important to read the plan details to determine which prescription drugs are covered and what the associated costs are [Northwind_Standard_Benefits_Details.pdf#page=91]. Additionally, employees should select in-network providers to maximize coverage and avoid unexpected costs, submit claims as soon as possible after a service is rendered, and track claims and follow up with Northwind Health if a claim is not processed in a timely manner [Northwind_Standard_Benefits_Details.pdf#page=17].\\n\\n'}",
                "{'role': 'user', 'content': 'What is included in my Northwind Health Plus plan that is not in standard?\\n\\nSources:\\nNorthwind_Health_Plus_Benefits_Details.pdf#page=100:    \u2022 Understand your coverage limits, and know what services are  covered and what services  are not covered...(truncated)\\nNorthwind_Standard_Benefits_Details.pdf#page=17:  Employees should keep track of their claims and follow up with  Northwind Health if a claim is not processed in a timely manner...(truncated)\\nNorthwind_Health_Plus_Benefits_Details.pdf#page=24:  It is important to talk to your doctor or  health care provider..(truncated)'}"
            ],
            "props": null
        }
    ]
    ```

    The app displays these thoughts in the "Thought process" tab, available by selecting the lightbulb icon on each answer. [See image](./images/thoughts.png)
