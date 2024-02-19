import traceback
from utils.database_handler import (
    get_party_instance,
    update_party_instance,
    delete_party_instance,
    get_parties,
    get_user_by_id,
    remove_party_member,
)
from utils.spotify_handler import (
    get_currently_playing,
    get_queue,
    get_recently_played,
    play_song,
)
import time
from fastapi_utils.tasks import repeat_every

currently_listening = {}


@repeat_every(seconds=5, raise_exceptions=True)
async def check_for_inactivity():
    for party_id in currently_listening.keys():
        e = await get_party_instance(party_id)
        if not e:
            currently_listening.pop(party_id)
        try:
            party_data = e["party_data"]
            if (
                abs(party_data["time_since_last_played"] - time.time()) >= 150
                and not party_data["is_playing"]
            ):
                currently_listening.pop(party_id)
                await delete_party_instance(party_id)
        except KeyError:
            continue
        except TypeError:
            currently_listening.pop(party_id)


@repeat_every(seconds=5, raise_exceptions=True)
async def add_new_parties():
    parties = await get_parties()

    async for party in parties:
        if party["_id"] not in currently_listening.keys():
            currently_listening[party["_id"]] = party["party_info"]["users"]


@repeat_every(seconds=5, raise_exceptions=True)
async def update_party_details():
    for party_id in currently_listening.keys():
        try:
            party = await get_party_instance(party_id)
            owner = await get_user_by_id(party["party_info"]["owner"])
            if not party:
                currently_listening.pop(party_id)
            owner_token = owner["spotify_session_data"]["access_token"]
            owner_currently_playing = await get_currently_playing(owner_token)
            party_data = {
                "is_playing": owner_currently_playing["is_playing"],
                "current_song": {},
                "time_since_last_played": round(time.time()),
                "queue": await get_queue(owner_token),
                "history": await get_recently_played(owner_token),
            }
            owner_current_song = owner_currently_playing
            del owner_current_song["is_playing"]
            party_data["current_song"] = owner_current_song
            party["party_data"] = party_data
            await update_party_instance(party_id, party)
        except Exception:
            traceback.print_exc()

            continue


@repeat_every(seconds=5, raise_exceptions=True)
async def update_playback():
    for party_id, users in currently_listening.items():
        party = await get_party_instance(party_id)
        if not party:
            currently_listening.pop(party_id)

        for user in users:
            if party["party_info"]["owner"] == user:
                continue
            user = await get_user_by_id(user)

            user_token = user["spotify_session_data"]["access_token"]
            user_currently_playing = await get_currently_playing(user_token)

            if not user_currently_playing["is_playing"]:
                await remove_party_member(party_id, user["_id"])

                continue
            if user_currently_playing["uri"] != party["party_data"]["current_song"][
                "uri"
            ] or not user_currently_playing["progress_ms"] in range(
                party["party_data"]["current_song"]["progress_ms"] - 1000,
                party["party_data"]["current_song"]["progress_ms"] + 1000,
            ):
                await play_song(
                    user_token,
                    party["party_data"]["current_song"]["uri"],
                    party["party_data"]["current_song"]["progress_ms"],
                )
