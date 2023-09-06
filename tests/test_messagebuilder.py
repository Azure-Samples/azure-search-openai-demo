from core.messagebuilder import MessageBuilder


def test_messagebuilder():
    builder = MessageBuilder("You are a bot.", "gpt-35-turbo")
    assert builder.messages == [
        # 1 token, 1 token, 1 token, 5 tokens
        {"role": "system", "content": "You are a bot."}
    ]
    assert builder.model == "gpt-35-turbo"
    assert builder.token_length == 8


def test_messagebuilder_append():
    builder = MessageBuilder("You are a bot.", "gpt-35-turbo")
    builder.append_message("user", "Hello, how are you?")
    assert builder.messages == [
        # 1 token, 1 token, 1 token, 5 tokens
        {"role": "system", "content": "You are a bot."},
        # 1 token, 1 token, 1 token, 6 tokens
        {"role": "user", "content": "Hello, how are you?"},
    ]
    assert builder.model == "gpt-35-turbo"
    assert builder.token_length == 17
