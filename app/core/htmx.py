import json

from fastapi import Response


def error_toast(message: str) -> Response:
    headers = {
        "HX-Trigger": json.dumps({"show-toast": {"message": message, "type": "error"}})
    }
    return Response(status_code=204, headers=headers)


def redirect(url: str) -> Response:
    return Response(status_code=204, headers={"HX-Redirect": url})
