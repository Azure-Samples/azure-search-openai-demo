import base64

import pytest

from core.imageshelper import calculate_image_token_cost, get_image_dims


@pytest.fixture
def small_image():
    return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z/C/HgAGgwJ/lK3Q6wAAAABJRU5ErkJggg=="


@pytest.fixture
def large_image():
    large_image = open("tests/image_large.png", "rb").read()
    img = base64.b64encode(large_image).decode("utf-8")
    return f"data:image/png;base64,{img}"


def test_calculate_image_token_cost(small_image, large_image):
    assert calculate_image_token_cost(small_image, "low") == 85
    assert calculate_image_token_cost(small_image, "high") == 255
    assert calculate_image_token_cost(small_image) == 255
    assert calculate_image_token_cost(large_image, "low") == 85
    assert calculate_image_token_cost(large_image, "high") == 1105
    with pytest.raises(ValueError, match="Invalid value for detail parameter."):
        assert calculate_image_token_cost(large_image, "medium")


def test_get_image_dims_small(small_image, large_image):
    assert get_image_dims(small_image) == (1, 1)
    assert get_image_dims(large_image) == (2050, 1238)
    with pytest.raises(ValueError, match="Image must be a base64 string."):
        assert get_image_dims("http://domain.com/image.png")
