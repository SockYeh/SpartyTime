import time

import jwt
from decouple import config

JWT_SECRET = config("secret")
JWT_ALGORITHM = config("algorithm")


def token_response(token: str) -> dict:
    return {"access_token": token}


def signJWT(user_id: str) -> dict:
    expiry = time.time() + 60 * 60 * 24 * 7
    payload = {"user_id": user_id, "expires": expiry}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token_response(token)


def decode_jwt(token: str) -> dict:
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        decoded_token["status"] = "Success"
        return (
            decoded_token
            if decoded_token["expires"] >= time.time()
            else {"status": "Expired"}
        )
    except Exception as e:
        return {"status": "Failed", "message": str(e)}
