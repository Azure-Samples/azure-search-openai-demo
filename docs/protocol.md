# HTTP protocol for RAG chat apps

We are standardizing on a common HTTP protocol across RAG chat app solutions and tools,
to make them more compatible with each other. By agreeing on a common protocol, developers
can swap different components, like using the Python backend from this repository
with a Web Components frontend from [azure-search-openai-javascript](https://github.com/Azure-Samples/azure-search-openai-javascript).

This protocol is inspired by the [OpenAI ChatCompletion API](https://platform.openai.com/docs/guides/text-generation/chat-completions-api),
but contains additional fields required for a RAG chat app.

## HTTP requests to RAG chat app endpoints

An HTTP request to `/chat` or `/ask` can contain these properties, in JSON:

* `"messages"`: A list of messages, each containing "content" and "role", where "role" may be "system", "assistant", or "user"
* `"stream"`: A boolean indicating whether the response should be streamed or not.
* `"context"`: An object containing any additional context about the request. This app only sets the "overrides" property, which is an object with additional settings for the request, like how many search results to return.
* `"session_state"`: An object containing the "memory" for the chat app, such as a user ID. Not currently used by this app.

Here's an example JSON request:

```json
{
    "messages": [
        {
            "content": "What is included in my Northwind Health Plus plan that is not in standard?",
            "role": "user"
        }
    ],
    "stream": false,
    "context": {
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
    },
    "session_state": null
}
```

## HTTP responses from RAG chat app endpoints

An HTTP response can either be JSON, for a non-streaming response, or newline-delimited JSON ("NDJSON"/"jsonlines") sent with the `HTTP Transfer-Encoding: Chunked` header.

In both cases, the response object is based on the
[OpenAI ChatCompletion response format](https://platform.openai.com/docs/api-reference/chat/object),
with additional properties needed to display sources and citations properly.

### Non-streaming response

This response is based off the [OpenAI chat completion object](https://platform.openai.com/docs/api-reference/chat/object),
with additional properties needed to display sources and citations properly.

A non-streaming JSON response contains the following properties:

* `"choices"`: A list of responses from the LLM, typically containing only 1 response as our app sets `n=1` when requesting a completion. Each response contains:
   * `"message"`: An object containing the actual content of the response. Copied directly from the OpenAI response.
   * `"finish_reason"`: A string representing the finish state of the response. Copied directly from the OpenAI response.
   * `"index"`: A number indicating which response this is (0 in the case of 1 response given). Copied directly from the OpenAI response.
   * `"content_filter_results"`: An object from the Azure Content Safety filter. Copied directly from the OpenAI response, but will only be returned when using Azure OpenAI, not openai.com OpenAI.
   * `"context"`: An object containing additional details needed for the RAG chat app. Includes:
       * `"data_points"`: An object containing text and/or image data chunks, a list in the `"text"` or `"images"` properties. Useful for citations.
       * `"thoughts"`: A list describing each step of the RAG approach, useful for a debug display in the RAG chat app.
   * `"session_state"`: An object containing the "memory" for the chat app, such as a user ID. Not currently used by this app.
* `"created"`: The Unix timestamp (in seconds) of when the chat completion was created. Copied directly from the OpenAI response.
* `"id"`: A unique identifier for the chat completion. Copied directly from the OpenAI response.
* `"model"`: The model used for the completion, such as "gpt-35-turbo". Copied directly from the OpenAI response.
* `"object"`: The object type, always "chat.completion". Copied directly from the OpenAI response.
* `"prompt_filter_results"`: Copied directly from the OpenAI response, but will only be returned when using Azure OpenAI, not openai.com OpenAI.
* `"system_fingerprint"`: Represents the backend configuration that the model runs with. Copied directly from the OpenAI response.
* `"usage"`: Usage statistics for the completion request. Copied directly from the OpenAI response.


Here's an example JSON response:

```json
{
    "choices": [
        {
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
            },
            "context": {
                "data_points": {
                    "text": [
                        "Northwind_Standard_Benefits_Details.pdf#page=91:    Tips for Avoiding Intentionally False Or Misleading Statements:   When it comes to understanding a health plan, it is important to be aware of any  intentiona lly false or misleading statements that the plan provider may make...(truncated)",
                        "Northwind_Standard_Benefits_Details.pdf#page=91:  It is important to  research the providers and services offered in the Northwind Standard plan i n order to  determine if the providers and services offered are sufficient for the employee's needs...(truncated)",
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
            "finish_reason": "stop",
            "index": 0,
            "message": {
                "content": "There is no specific information provided about what is included in the Northwind Health Plus plan that is not in the standard plan. It is recommended to read the plan details carefully and ask questions to understand the specific benefits of the Northwind Health Plus plan [Northwind_Standard_Benefits_Details.pdf#page=91].",
                "function_call": null,
                "role": "assistant",
                "tool_calls": null
            },
            "session_state": null
        }
    ],
    "created": 1706301586,
    "id": "chatcmpl-8lNHGormHX5fhozITxASIufDZno9D",
    "model": "gpt-35-turbo",
    "object": "chat.completion",
    "prompt_filter_results": [
        {
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
            },
            "prompt_index": 0
        }
    ],
    "system_fingerprint": null,
    "usage": {
        "completion_tokens": 64,
        "prompt_tokens": 967,
        "total_tokens": 1031
    }
}
```

### Streaming response

This response is based off the [OpenAI chat completion chunk object](https://platform.openai.com/docs/api-reference/chat/streaming),
with additional properties needed to display sources and citations properly.

The first chunk contains a choice with the `context` property, since that is available before the answer, and subsequent chunks contain the answer to the question.

* `"choices"`: A list of responses from the LLM, typically containing only 1 response as our app sets `n=1` when requesting a completion. Each response contains:
   * `"delta"`: An object containing the actual content of the response. Copied directly from the OpenAI response.
   * `"finish_reason"`: A string representing the finish state of the response. Copied directly from the OpenAI response.
   * `"index"`: A number indicating which response this is (0 in the case of 1 response given). Copied directly from the OpenAI response.
   * `"content_filter_results"`: An object from the Azure Content Safety filter. Copied directly from the OpenAI response, but will only be returned when using Azure OpenAI, not openai.com OpenAI.
   * `"context"`: An object containing additional details needed for the RAG chat app. Includes:
       * `"data_points"`: An object containing text and/or image data chunks, a list in the `"text"` or `"images"` properties. Useful for citations.
       * `"thoughts"`: A list describing each step of the RAG approach, useful for a debug display in the RAG chat app.
   * `"session_state"`: An object containing the "memory" for the chat app, such as a user ID. Not currently used by this app.
* `"created"`: The Unix timestamp (in seconds) of when the chat completion was created. Copied directly from the OpenAI response.
* `"id"`: A unique identifier for the chat completion. Copied directly from the OpenAI response.
* `"model"`: The model used for the completion, such as "gpt-35-turbo". Copied directly from the OpenAI response.
* `"object"`: The object type, always "chat.completion". Copied directly from the OpenAI response.
* `"prompt_filter_results"`: Copied directly from the OpenAI response, but will only be returned when using Azure OpenAI, not openai.com OpenAI.
* `"system_fingerprint"`: Represents the backend configuration that the model runs with. Copied directly from the OpenAI response.
* `"usage"`: Usage statistics for the completion request. Copied directly from the OpenAI response.


Here's an example of the first two JSON objects streamed for a `/chat` request:

```json
{
    "choices": [
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
            "finish_reason": null,
            "index": 0
        }
    ],
    "object": "chat.completion.chunk"
}{
    "id": "chatcmpl-8lNX48CGv9kW7vXTCa9Jb0J4RfnlQ",
    "choices": [
        {
            "delta": {
                "content": null,
                "function_call": null,
                "role": "assistant",
                "tool_calls": null
            },
            "finish_reason": null,
            "index": 0,
            "content_filter_results": {}
        }
    ],
    "created": 1706302566,
    "model": "gpt-35-turbo",
    "object": "chat.completion.chunk",
    "system_fingerprint": null
}
```
