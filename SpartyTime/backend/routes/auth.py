import base64
import logging
import os
import urllib.parse

import aiohttp
import six
from dotenv import find_dotenv, load_dotenv
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

from ..utils.database_handler import create_user, get_user_by_id
from ..utils.logger_handler import LoggerFormatter
from ..utils.spotify_handler import get_spotify_details, update_user_genre

load_dotenv(find_dotenv())

SPOTIFY_CLIENT_ID = os.environ["SPOTIFY_CLIENT_ID"]
SPOTIFY_CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]
REDIRECT_URL = os.environ["REDIRECT_URL"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(LoggerFormatter())
logger.addHandler(stream_handler)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login() -> RedirectResponse:
    """Login API endpoint for spotify authentication"""
    return RedirectResponse(
        f"https://accounts.spotify.com/authorize?response_type=code&client_id={SPOTIFY_CLIENT_ID}&scope=user-read-playback-state+user-modify-playback-state+user-read-currently-playing+user-library-read+user-top-read+user-library-read+user-follow-read+user-read-private+playlist-read-private+user-read-currently-playing+user-read-recently-played&redirect_uri={urllib.parse.quote_plus(REDIRECT_URL)}"
    )


@router.get(
    f"/callback",
)
async def callback(request: Request, code: str):
    """Callback API endpoint for spotify authentication"""
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
        await create_user(user_data, dat)
        resp.status_code = status.HTTP_201_CREATED
        logger.info(f"User {user_data['id']} created")

    user = await get_user_by_id(user_data["id"], is_spotify_id=True)

    request.session["user_id"] = str(user.id)
    await update_user_genre(str(user.id))
    return RedirectResponse(
        str(request.url_for("home")), status_code=status.HTTP_302_FOUND
    )


@router.get("/me", status_code=status.HTTP_200_OK, response_class=JSONResponse)
async def me(request: Request):
    """API endpoint to get user data from currently authenticated Spotify user"""

    try:
        token = request.cookies.get("session")
        if token:
            user_id = request.session["user_id"]
            user = await get_user_by_id(user_id)
            access_token = user.spotify_session_data.access_token
            user_data = await get_spotify_details(access_token)

            return JSONResponse(content=user_data)
        else:
            return JSONResponse(
                content={"error": "no session cookie found"},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
    except Exception:
        return JSONResponse(
            content={"error": "invalid/expired token"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
