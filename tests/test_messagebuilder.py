from core.messagebuilder import MessageBuilder


def test_messagebuilder():
    builder = MessageBuilder("You are a bot.", "gpt-35-turbo")
    assert builder.messages == [
        # 1 token, 1 token, 1 token, 5 tokens
        {"role": "system", "content": "You are a bot."}
    ]
    assert builder.model == "gpt-35-turbo"
    assert builder.count_tokens_for_message(builder.messages[0]) == 8


def test_messagebuilder_append():
    builder = MessageBuilder("You are a bot.", "gpt-35-turbo")
    builder.insert_message("user", "Hello, how are you?")
    assert builder.messages == [
        # 1 token, 1 token, 1 token, 5 tokens
        {"role": "system", "content": "You are a bot."},
        # 1 token, 1 token, 1 token, 6 tokens
        {"role": "user", "content": "Hello, how are you?"},
    ]
    assert builder.model == "gpt-35-turbo"
    assert builder.count_tokens_for_message(builder.messages[0]) == 8
    assert builder.count_tokens_for_message(builder.messages[1]) == 9


def test_messagebuilder_unicode():
    builder = MessageBuilder("a\u0301", "gpt-35-turbo")
    assert builder.messages == [
        # 1 token, 1 token, 1 token, 1 token
        {"role": "system", "content": "á"}
    ]
    assert builder.model == "gpt-35-turbo"
    assert builder.count_tokens_for_message(builder.messages[0]) == 4


def test_messagebuilder_unicode_append():
    builder = MessageBuilder("a\u0301", "gpt-35-turbo")
    builder.insert_message("user", "a\u0301")
    assert builder.messages == [
        # 1 token, 1 token, 1 token, 1 token
        {"role": "system", "content": "á"},
        # 1 token, 1 token, 1 token, 1 token
        {"role": "user", "content": "á"},
    ]
    assert builder.model == "gpt-35-turbo"
    assert builder.count_tokens_for_message(builder.messages[0]) == 4
    assert builder.count_tokens_for_message(builder.messages[1]) == 4
