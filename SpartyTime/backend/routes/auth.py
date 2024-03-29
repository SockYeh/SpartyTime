import base64
import os
import urllib.parse

import aiohttp
import six
from dotenv import load_dotenv
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from utils.database_handler import create_user, get_user_by_id
from utils.jwt_handler import decode_jwt, signJWT
from utils.spotify_handler import get_spotify_details, update_user_genre

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URL = os.getenv("REDIRECT_URL")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login():
    return RedirectResponse(
        f"https://accounts.spotify.com/authorize?response_type=code&client_id={SPOTIFY_CLIENT_ID}&scope=user-read-playback-state+user-modify-playback-state+user-read-currently-playing+user-library-read+user-top-read+user-library-read+user-follow-read+user-read-private+playlist-read-private+user-read-currently-playing+user-read-recently-played&redirect_uri={urllib.parse.quote_plus(REDIRECT_URL)}"
    )


# playlist-read-private user-modify-playback-state user-library-read user-follow-read user-read-playback-state user-read-currently-playing user-read-recently-played user-top-read user-read-private


@router.get(f"/callback/")
async def callback(request: Request, code: str):
    auth_header = base64.b64encode(
        six.text_type(SPOTIFY_CLIENT_ID + ":" + SPOTIFY_CLIENT_SECRET).encode("ascii")
    )
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://accounts.spotify.com/api/token",
            headers={
                "Authorization": f"Basic {auth_header.decode('ascii')}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "redirect_uri": f"{REDIRECT_URL}",
                "code": code,
                "grant_type": "authorization_code",
            },
        ) as resp:
            dat = await resp.json()
    try:
        user_data = await get_spotify_details(dat["access_token"])

    except KeyError:
        return RedirectResponse(
            str(request.url_for("login")), status_code=status.HTTP_401_UNAUTHORIZED
        )
    await create_user(user_data, dat)
    resp = JSONResponse(content={})

    if not await get_user_by_id(user_data["id"], is_spotify_id=True):
        await create_user(user_data)
        resp.status_code = status.HTTP_201_CREATED

    user = await get_user_by_id(user_data["id"], is_spotify_id=True)

    jwt_token = signJWT(
        user["_id"],
    )
    resp.set_cookie(key="session", value=jwt_token["access_token"])
    await update_user_genre(user["_id"])
    return resp


@router.get("/me")
async def me(request: Request):
    try:
        jwt_token = request.cookies.get("session")
        if jwt_token:
            user_id = decode_jwt(jwt_token)["user_id"]
            user = await get_user_by_id(user_id)
            access_token = user["spotify_session_data"]["access_token"]
            user_data = await get_spotify_details(access_token)
            return user_data
        else:
            return {"error": "no session cookie found"}
    except Exception:
        return {"error": "invalid/expired token"}


if __name__ == "__main__":
    os.system("uvicorn main:router --reload")
