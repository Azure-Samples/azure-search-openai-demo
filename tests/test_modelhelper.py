import pytest

from core.modelhelper import (
    get_oai_chatmodel_tiktok,
    get_token_limit,
    num_tokens_from_messages,
)


def test_get_token_limit():
    assert get_token_limit("gpt-35-turbo") == 4000
    assert get_token_limit("gpt-3.5-turbo") == 4000
    assert get_token_limit("gpt-35-turbo-16k") == 16000
    assert get_token_limit("gpt-3.5-turbo-16k") == 16000
    assert get_token_limit("gpt-4") == 8100
    assert get_token_limit("gpt-4-32k") == 32000


def test_get_token_limit_error():
    with pytest.raises(ValueError, match="Expected model gpt-35-turbo and above"):
        get_token_limit("gpt-3")


def test_num_tokens_from_messages():
    message = {
        # 1 token : 1 token
        "role": "user",
        # 1 token : 5 tokens
        "content": "Hello, how are you?",
    }
    model = "gpt-35-turbo"
    assert num_tokens_from_messages(message, model) == 9


def test_num_tokens_from_messages_gpt4():
    message = {
        # 1 token : 1 token
        "role": "user",
        # 1 token : 5 tokens
        "content": "Hello, how are you?",
    }
    model = "gpt-4"
    assert num_tokens_from_messages(message, model) == 9


def test_get_oai_chatmodel_tiktok_mapped():
    assert get_oai_chatmodel_tiktok("gpt-35-turbo") == "gpt-3.5-turbo"
    assert get_oai_chatmodel_tiktok("gpt-35-turbo-16k") == "gpt-3.5-turbo-16k"


def test_get_oai_chatmodel_tiktok_unmapped():
    assert get_oai_chatmodel_tiktok("gpt-4") == "gpt-4"


def test_get_oai_chatmodel_tiktok_error():
    with pytest.raises(ValueError, match="Expected Azure OpenAI ChatGPT model name"):
        get_oai_chatmodel_tiktok("")
    with pytest.raises(ValueError, match="Expected Azure OpenAI ChatGPT model name"):
        get_oai_chatmodel_tiktok(None)
    with pytest.raises(ValueError, match="Expected Azure OpenAI ChatGPT model name"):
        get_oai_chatmodel_tiktok("gpt-3")
