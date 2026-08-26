"""
Response helpers
"""

from fastapi.responses import JSONResponse


def success(data=None, message: str = "success"):
    return JSONResponse(content={
        "code": 0,
        "message": message,
        "data": data
    })


def error(message: str = "error", code: int = 400):
    return JSONResponse(
        status_code=code,
        content={
            "code": code,
            "message": message,
            "data": None
        }
    )
