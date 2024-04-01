from bson.objectid import ObjectId
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from utils.database_handler import (
    get_parties,
    get_user_by_id,
    aggregate_party,
)
from utils.jwt_handler import decode_jwt
from utils.session_manager import validate_session


router = APIRouter(
    prefix="/discovery",
    tags=["discovery", "discover"],
    dependencies=[Depends(validate_session)],
)


async def convert_bsons_to_str(data: list) -> list:
    for item in data:
        item._id = str(item._id)
        item.party_info.owner = str(item.party_info.owner)
        item.party_info.users = [str(user) for user in item.party_info.users]
    return data


@router.get("/parties")
async def get_all_parties(request: Request):
    parties = await get_parties()

    return JSONResponse(
        content={"parties": await convert_bsons_to_str(parties)},
        status_code=status.HTTP_200_OK,
    )


@router.get("/parties/{genre}")
async def get_parties_by_genre(request: Request, genre: str):
    parties = await get_parties({"party_info.genres": genre})

    return JSONResponse(
        content={"parties": await convert_bsons_to_str(parties)},
        status_code=status.HTTP_200_OK,
    )


@router.get("/match-user")
async def match_genres(request: Request):
    userid = decode_jwt(request.cookies["session"])["user_id"]
    user = await get_user_by_id(userid)
    user_genres = user.genres
    parties = await aggregate_party(
        [
            {
                "$match": {
                    "party_info.genres": {"$in": user_genres},
                    "party_info.users": {"$nin": [ObjectId(userid)]},
                }
            },
            {
                "$project": {
                    "party_info": 1,
                    "party_data": 1,
                    "intersection": {
                        "$size": {
                            "$setIntersection": ["$party_info.genres", user_genres]
                        }
                    },
                }
            },
            {"$sort": {"intersection": -1}},
        ]
    )
    return JSONResponse(
        content={"parties": await convert_bsons_to_str(parties)},
        status_code=status.HTTP_200_OK,
    )
