import logging

from openai import APIError
from quart import jsonify

ERROR_MESSAGE = """Oops! GovGPT needs to take a break. As this is a proof of concept, we have limited capacity. Please try again later."""

ERROR_MESSAGE_FILTER = """Sorry. Your message contains content that is automatically flagged by the built-in content filter. Please try a different topic or question that avoids themes of hate, violence, harm or sex. If you are in danger or an emergency situation, please contact 111."""

ERROR_MESSAGE_LENGTH = """Oops! Your question is too long. As this is a proof of concept, we have limited capacity. Please try to keep your question to about 75 words."""


def error_dict(error: Exception) -> dict:
    if isinstance(error, APIError) and error.code == "content_filter":
        return {"error": ERROR_MESSAGE_FILTER}
    if isinstance(error, APIError) and error.code == "context_length_exceeded":
        return {"error": ERROR_MESSAGE_LENGTH}
    return {"error": ERROR_MESSAGE.format(error_type=type(error))}


def error_response(error: Exception, route: str, status_code: int = 500):
    logging.exception("Exception in %s: %s", route, error)
    if isinstance(error, APIError) and error.code == "content_filter":
        status_code = 400
    return jsonify(error_dict(error)), status_code
