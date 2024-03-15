import logging

from openai import APIError
from quart import jsonify

ERROR_MESSAGE = """The app encountered an error processing your request.
If you are an administrator of the app, view the full error in the logs. See aka.ms/appservice-logs for more information.
Error type: {error_type}
"""
ERROR_MESSAGE_FILTER = """Your message contains content that was flagged by the OpenAI content filter."""


def error_dict(error: Exception) -> dict:
    if isinstance(error, APIError) and error.code == "content_filter":
        return {"error": ERROR_MESSAGE_FILTER}
    return {"error": ERROR_MESSAGE.format(error_type=type(error))}


def error_response(error: Exception, route: str, status_code: int = 500):
    logging.exception("Exception in %s: %s", route, error)
    if isinstance(error, APIError) and error.code == "content_filter":
        status_code = 400
    return jsonify(error_dict(error)), status_code
