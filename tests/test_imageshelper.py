import base64

from core.imageshelper import calculate_image_token_cost, get_image_dims

TEST_IMAGE = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z/C/HgAGgwJ/lK3Q6wAAAABJRU5ErkJggg=="


def test_calculate_image_token_cost():
    assert calculate_image_token_cost(TEST_IMAGE, "low") == 85
    assert calculate_image_token_cost(TEST_IMAGE, "high") == 255
    assert calculate_image_token_cost(TEST_IMAGE) == 255


def test_get_image_dims():
    assert get_image_dims(TEST_IMAGE) == (1, 1)

    large_image = open("tests/image_large.png", "rb").read()
    img = base64.b64encode(large_image).decode("utf-8")
    encoded = f"data:image/png;base64,{img}"
    assert get_image_dims(encoded) == (960, 580)
