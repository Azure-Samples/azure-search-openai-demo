import json

from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach


def test_get_search_query():
    chat_approach = ChatReadRetrieveReadApproach(None, "", "gpt-35-turbo", "gpt-35-turbo", "", "", "", "")

    payload = '{"id":"chatcmpl-81JkxYqYppUkPtOAia40gki2vJ9QM","object":"chat.completion","created":1695324963,"model":"gpt-35-turbo","prompt_filter_results":[{"prompt_index":0,"content_filter_results":{"hate":{"filtered":false,"severity":"safe"},"self_harm":{"filtered":false,"severity":"safe"},"sexual":{"filtered":false,"severity":"safe"},"violence":{"filtered":false,"severity":"safe"}}}],"choices":[{"index":0,"finish_reason":"function_call","message":{"role":"assistant","function_call":{"name":"search_sources","arguments":"{\\n\\"search_query\\":\\"accesstelemedicineservices\\"\\n}"}},"content_filter_results":{}}],"usage":{"completion_tokens":19,"prompt_tokens":425,"total_tokens":444}}'
    default_query = "hello"
    query = chat_approach.get_search_query(json.loads(payload), default_query)

    assert query == "accesstelemedicineservices"


def test_get_search_query_returns_default():
    chat_approach = ChatReadRetrieveReadApproach(None, "", "gpt-35-turbo", "gpt-35-turbo", "", "", "", "")

    payload = '{"id":"chatcmpl-81JkxYqYppUkPtOAia40gki2vJ9QM","object":"chat.completion","created":1695324963,"model":"gpt-35-turbo","prompt_filter_results":[{"prompt_index":0,"content_filter_results":{"hate":{"filtered":false,"severity":"safe"},"self_harm":{"filtered":false,"severity":"safe"},"sexual":{"filtered":false,"severity":"safe"},"violence":{"filtered":false,"severity":"safe"}}}],"choices":[{"index":0,"finish_reason":"function_call","message":{"role":"assistant"},"content_filter_results":{}}],"usage":{"completion_tokens":19,"prompt_tokens":425,"total_tokens":444}}'
    default_query = "hello"
    query = chat_approach.get_search_query(json.loads(payload), default_query)

    assert query == default_query


def test_get_messages_from_history():
    chat_approach = ChatReadRetrieveReadApproach(None, "", "gpt-35-turbo", "gpt-35-turbo", "", "", "", "")

    messages = chat_approach.get_messages_from_history(
        system_prompt="You are a bot.",
        model_id="gpt-35-turbo",
        history=[
            {
                "user": "What happens in a performance review?",
                "bot": "During the performance review at Contoso Electronics, the supervisor will discuss the employee's performance over the past year and provide feedback on areas for improvement. They will also provide an opportunity for the employee to discuss their goals and objectives for the upcoming year. The review is a two-way dialogue between managers and employees, and employees will receive a written summary of their performance review which will include a rating of their performance, feedback, and goals and objectives for the upcoming year [employee_handbook-3.pdf].",
            },
            {"user": "What does a Product Manager do?"},
        ],
        user_content="What does a Product Manager do?",
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


def test_get_messages_from_history_truncated():
    chat_approach = ChatReadRetrieveReadApproach(None, "", "gpt-35-turbo", "gpt-35-turbo", "", "", "", "")

    messages = chat_approach.get_messages_from_history(
        system_prompt="You are a bot.",
        model_id="gpt-35-turbo",
        history=[
            {
                "user": "What happens in a performance review?",
                "bot": "During the performance review at Contoso Electronics, the supervisor will discuss the employee's performance over the past year and provide feedback on areas for improvement. They will also provide an opportunity for the employee to discuss their goals and objectives for the upcoming year. The review is a two-way dialogue between managers and employees, and employees will receive a written summary of their performance review which will include a rating of their performance, feedback, and goals and objectives for the upcoming year [employee_handbook-3.pdf].",
            },
            {"user": "What does a Product Manager do?"},
        ],
        user_content="What does a Product Manager do?",
        max_tokens=10,
    )
    assert messages == [
        {"role": "system", "content": "You are a bot."},
        {"role": "user", "content": "What does a Product Manager do?"},
    ]


def test_get_messages_from_history_truncated_longer():
    chat_approach = ChatReadRetrieveReadApproach(None, "", "gpt-35-turbo", "gpt-35-turbo", "", "", "", "")

    messages = chat_approach.get_messages_from_history(
        system_prompt="You are a bot.",
        model_id="gpt-35-turbo",
        history=[
            {
                "user": "What happens in a performance review?",
                "bot": "During the performance review at Contoso Electronics, the supervisor will discuss the employee's performance over the past year and provide feedback on areas for improvement. They will also provide an opportunity for the employee to discuss their goals and objectives for the upcoming year. The review is a two-way dialogue between managers and employees, and employees will receive a written summary of their performance review which will include a rating of their performance, feedback, and goals and objectives for the upcoming year [employee_handbook-3.pdf].",
            },
            {
                "user": "Is there a dress code?",
                "bot": "Yes, there is a dress code at Contoso Electronics. Look sharp! [employee_handbook-1.pdf]",
            },
            {"user": "What does a Product Manager do?"},
        ],
        user_content="What does a Product Manager do?",
        max_tokens=30,
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
