from fastapi import HTTPException, Request

from .jwt_handler import decode_jwt


async def validate_session(request: Request):
    try:
        decoded_jwt = decode_jwt(request.cookies["session"])
        if decoded_jwt["status"] == "Failed" or decoded_jwt["status"] == "Expired":
            raise HTTPException(status_code=401, detail="Invalid Session!")
    except KeyError:
        raise HTTPException(status_code=401, detail="Invalid Session!")
