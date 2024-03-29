import time

import jwt, os
from dotenv import load_dotenv
import pydantic
from bson import ObjectId
from bson.errors import InvalidId

load_dotenv()

JWT_SECRET = os.environ["secret"]
JWT_ALGORITHM = os.environ["algorithm"]


class JWTExpired(Exception):
    def __init__(self) -> None:
        super().__init__("JWT token has expired. ")


class JWTToken(pydantic.BaseModel):
    user_id: str
    expires: float = time.time() + 60 * 60 * 24 * 7

    @pydantic.validator("user_id", pre=True, always=True)
    def check_user_id(cls, value):
        if not ObjectId.is_valid(value):
            raise InvalidId(f"{value} is not a valid ObjectId. ")
        return value

    @pydantic.validator("expires", pre=True, always=True)
    def check_expiry(cls, value):
        if value < time.time():
            raise JWTExpired()
        return value


def token_response(token: str) -> dict:
    return {"access_token": token}


def signJWT(user_id: str) -> dict:
    payload: dict = JWTToken(user_id=user_id).dict()
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token_response(token)


def decode_jwt(token: str) -> dict:
    decoded_token: dict = JWTToken(
        **jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    ).dict()
    return decoded_token
