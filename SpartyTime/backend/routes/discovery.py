import time, json
from typing import Optional

from bson.objectid import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from utils.database_handler import get_parties, get_user_by_id, get_party
from utils.jwt_handler import decode_jwt
from utils.session_manager import validate_session


router = APIRouter(
    prefix="/discovery",
    tags=["discovery", "discover"],
    dependencies=[Depends(validate_session)],
)


async def convert_bsons_to_str(data: list) -> list:
    for item in data:
        item["_id"] = str(item["_id"])
        item["party_info"]["owner"] = str(item["party_info"]["owner"])
        item["party_info"]["users"] = [
            str(user) for user in item["party_info"]["users"]
        ]
    return data


@router.get("/parties")
async def get_all_parties(request: Request):
    parties = await get_parties()
    parties = [(party) async for party in parties]
    return JSONResponse(
        content={"parties": await convert_bsons_to_str(parties)},
        status_code=status.HTTP_200_OK,
    )


@router.get("/parties/{genre}")
async def get_parties_by_genre(request: Request, genre: str):
    parties = await get_parties({"party_info.genres": genre})
    parties = [(party) async for party in parties]

    return JSONResponse(
        content={"parties": await convert_bsons_to_str(parties)},
        status_code=status.HTTP_200_OK,
    )


@router.get("/match-user")
async def match_genres(request: Request):
    userid = decode_jwt(request.cookies["session"])["user_id"]
    user = await get_user_by_id(userid)
    user_genres = user["top_genres"]
    parties = await get_party(
        {"party_info.genres": {"$setIsSubset": [user_genres, "$party_info.genres"]}} # broken 
    )
    parties = [(party) async for party in parties]
    return JSONResponse(
        content={"parties": await convert_bsons_to_str(parties)},
        status_code=status.HTTP_200_OK,
    )
