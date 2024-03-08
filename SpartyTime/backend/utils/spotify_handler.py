import base64
import os
import traceback

import aiohttp
import six
from dotenv import load_dotenv

from .database_handler import (
    get_user_by_access_token,
    get_user_by_id,
    update_session,
    get_users,
    update_user,
)

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
session = None


async def create_session():
    global session
    session = aiohttp.ClientSession()


async def close_session():
    await session.close()


def get_headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/x-www-form-urlencoded",
    }


def parse_items_json(items: dict, type: str = "recent"):
    parse_with = "items"
    if type == "queue":
        parse_with = "queue"

    return [
        {
            "name": item["name"] if type != "recent" else item["track"]["name"],
            "uri": (item["uri"] if type != "recent" else item["track"]["uri"]).split(
                ":"
            )[2],
            "album": {
                "name": (
                    item["album"]["name"]
                    if type != "recent"
                    else item["track"]["album"]["name"]
                ),
                "uri": (
                    item["album"]["uri"]
                    if type != "recent"
                    else item["track"]["album"]["uri"]
                ).split(":")[2],
                "image": (
                    item["album"]["images"][0]["url"]
                    if type != "recent"
                    else item["track"]["album"]["images"][0]["url"]
                ),
            },
            "artists": [
                {
                    "name": artist["name"],
                    "uri": artist["uri"].split(":")[2],
                }
                for artist in (
                    item["artists"] if type != "recent" else item["track"]["artists"]
                )
            ],
        }
        for item in items[parse_with]
    ]


async def get_spotify_details(access_token: str):
    session = aiohttp.ClientSession()

    async with session.get(
        f"https://api.spotify.com/v1/me",
        headers=get_headers(access_token),
    ) as resp:
        if resp.status == 401:
            try:
                user = await get_user_by_access_token(access_token)
                userid = user["_id"]
                spotify_auth_data = await refresh_token(userid)
                access_token = spotify_auth_data["access_token"]
                return await get_spotify_details(access_token)
            except Exception:
                return traceback.format_exc()
        return await resp.json()


async def refresh_token(userid: str):
    userdata = await get_user_by_id(userid)
    refresh_token = userdata["spotify_session_data"]["refresh_token"]

    auth_header = base64.b64encode(
        six.text_type(SPOTIFY_CLIENT_ID + ":" + SPOTIFY_CLIENT_SECRET).encode("ascii")
    )

    async with session.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {auth_header.decode('ascii')}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    ) as resp:
        dat = await resp.json()

    session_data = {}
    session_data["access_token"] = dat["access_token"]
    session_data["expires_in"] = dat["expires_in"]
    session_data["scope"] = dat["scope"]
    session_data["token_type"] = dat["token_type"]
    session_data["refresh_token"] = refresh_token

    e = await update_session(userid, session_data)
    if e:
        return session_data

    return {"error": e}


async def get_currently_playing(access_token: str) -> dict:
    async with session.get(
        f"https://api.spotify.com/v1/me/player/currently-playing",
        headers=get_headers(access_token),
    ) as resp:
        if resp.status == 401:
            try:
                user = await get_user_by_access_token(access_token)
                userid = user["_id"]
                spotify_auth_data = await refresh_token(userid)
                access_token = spotify_auth_data["access_token"]
                return await get_currently_playing(access_token)
            except Exception:
                return traceback.format_exc()
        resp_json = await resp.json()
        return {
            "is_playing": resp_json["is_playing"],
            "progress_ms": resp_json["progress_ms"],
            "name": resp_json["item"]["name"],
            "uri": (resp_json["item"]["uri"]).split(":")[2],
            "album": {
                "name": resp_json["item"]["album"]["name"],
                "uri": resp_json["item"]["album"]["uri"],
                "image": resp_json["item"]["album"]["images"][0]["url"],
            },
            "artists": [
                {
                    "name": artist["name"],
                    "uri": artist["uri"],
                }
                for artist in resp_json["item"]["artists"]
            ],
        }


async def get_recently_played(access_token: str, unix_timestamp: int = None):
    async with session.get(
        (
            f"https://api.spotify.com/v1/me/player/recently-played?limit=5&after={unix_timestamp}"
            if unix_timestamp
            else f"https://api.spotify.com/v1/me/player/recently-played?limit=5"
        ),
        headers=get_headers(access_token),
    ) as resp:
        await resp.json()
        if resp.status == 401:
            try:
                user = await get_user_by_access_token(access_token)
                userid = user["_id"]
                spotify_auth_data = await refresh_token(userid)
                access_token = spotify_auth_data["access_token"]
                return await get_recently_played(access_token)
            except Exception:
                return traceback.format_exc()
        return parse_items_json(await resp.json())


async def get_queue(access_token: str):
    async with session.get(
        f"https://api.spotify.com/v1/me/player/queue?limit=5",
        headers=get_headers(access_token),
    ) as resp:
        if resp.status == 401:
            try:
                user = await get_user_by_access_token(access_token)
                userid = user["_id"]
                spotify_auth_data = await refresh_token(userid)
                access_token = spotify_auth_data["access_token"]
                return await get_queue(access_token)
            except Exception:
                return traceback.format_exc()
        return parse_items_json(await resp.json(), "queue")


async def play_song(access_token: str, uri: str, position_ms: int = 0):
    headers = get_headers(access_token)
    headers["Content-Type"] = "application/json"
    async with session.put(
        f"https://api.spotify.com/v1/me/player/play",
        headers=headers,
        json={"uris": [uri], "position_ms": position_ms},
    ) as resp:
        if resp.status == 401:
            try:
                user = await get_user_by_access_token(access_token)
                userid = user["_id"]
                spotify_auth_data = await refresh_token(userid)
                access_token = spotify_auth_data["access_token"]
                return await play_song(access_token, uri)
            except Exception:
                return traceback.format_exc()
        return resp.status


async def get_several_tracks(access_token: str, uris: list):
    headers = get_headers(access_token)
    async with session.get(
        f"https://api.spotify.com/v1/tracks?ids={','.join(uris)}", headers=headers
    ) as resp:
        if resp.status == 401:
            try:
                user = await get_user_by_access_token(access_token)
                userid = user["_id"]
                spotify_auth_data = await refresh_token(userid)
                access_token = spotify_auth_data["access_token"]
                return await get_several_tracks(access_token, uris)
            except Exception:
                return traceback.format_exc()
        return await resp.json()


async def get_top_artist_genres(access_token: str):
    headers = get_headers(access_token)
    async with session.get(
        f"https://api.spotify.com/v1/me/top/artists", headers=headers
    ) as resp:
        if resp.status == 401:
            try:
                user = await get_user_by_access_token(access_token)
                userid = user["_id"]
                spotify_auth_data = await refresh_token(userid)
                access_token = spotify_auth_data["access_token"]
                return await get_top_artist_genres(access_token)
            except Exception:
                return traceback.format_exc()

        genres = {}
        for artist in (await resp.json())["items"]:
            for genre in artist["genres"]:
                if genre in genres:
                    genres[genre] += 1
                else:
                    genres[genre] = 1

        return sorted(list(genres.keys()), key=lambda x: genres[x], reverse=True)


async def update_user_genre(user: str = None, all: bool = True):

    if all:
        users = await get_users()
    else:
        users = [user]

    async for user in users:
        user_token = user["spotify_session_data"]["access_token"]
        resp = await get_top_artist_genres(user_token)
        user["top_genres"] = resp[:5]
        await update_user(user["_id"], user)


async def get_song(access_token: str, uri: str):
    headers = get_headers(access_token)
    async with session.get(
        f"https://api.spotify.com/v1/tracks/{uri}", headers=headers
    ) as resp:
        if resp.status == 401:
            try:
                user = await get_user_by_access_token(access_token)
                userid = user["_id"]
                spotify_auth_data = await refresh_token(userid)
                access_token = spotify_auth_data["access_token"]
                return await get_song(access_token, uri)
            except Exception:
                return traceback.format_exc()
        return await resp.json()


async def get_several_artists(access_token: str, uris: list):
    headers = get_headers(access_token)
    async with session.get(
        f"https://api.spotify.com/v1/artists?ids={','.join(uris)}", headers=headers
    ) as resp:
        if resp.status == 401:
            try:
                user = await get_user_by_access_token(access_token)
                userid = user["_id"]
                spotify_auth_data = await refresh_token(userid)
                access_token = spotify_auth_data["access_token"]
                return await get_several_artists(access_token, uris)
            except Exception:
                return traceback.format_exc()
        return await resp.json()
