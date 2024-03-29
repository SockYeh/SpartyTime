import time
from typing import Optional

from bson.objectid import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from utils.database_handler import (
    create_party_instance,
    delete_party_instance,
    get_party_instance,
    update_party_instance,
)
from utils.jwt_handler import decode_jwt
from utils.session_manager import validate_session


router = APIRouter(
    prefix="/parties", tags=["parties"], dependencies=[Depends(validate_session)]
)


class Party(BaseModel):
    party_name: str
    party_description: Optional[str] = None
    users: Optional[list[str]] = []
    type: str


class UpdateParty(BaseModel):
    party_name: Optional[str] = None
    party_description: Optional[str] = None
    owner: Optional[str] = None
    type: Optional[str] = None


async def is_owner(request: Request, party_id: str):
    auth_header = request.cookies["session"]
    userid = decode_jwt(auth_header)["user_id"]
    e = await get_party_instance(party_id)
    if not e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Party not found. {str(e)}"
        )
    if e["party_info"]["owner"] != userid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Unauthorized. {str(e)}"
        )
    return True


@router.post("/party", status_code=status.HTTP_201_CREATED)
async def create_party(request: Request, payload: Party):
    auth_header = request.cookies["session"]
    userid = decode_jwt(auth_header)["user_id"]
    party_dict = {
        "party_info": {
            "party_name": payload.party_name,
            "party_description": (
                payload.party_description
                if payload.party_description
                else "This is a party."
            ),
            "start": round(time.time()),
            "users": payload.users,
            "owner": userid,
            "type": payload.type,
        }
    }
    e = await create_party_instance(party_dict)
    if not e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Party creation failed. {str(e)}",
        )
    return JSONResponse(content={"id": str(e)})


@router.get(
    "/party/{party_id}",
    status_code=status.HTTP_200_OK,
)
async def get_party(request: Request, party_id: str):
    e = await get_party_instance(party_id)
    if not e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Party not found. {str(e)}"
        )
    return JSONResponse(content={"party": (e)})


@router.patch(
    "/party/{party_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(is_owner)],
)
async def update_party(request: Request, party_id: str, payload: UpdateParty):
    converted = payload.dict(exclude_none=True)

    e = await update_party_instance(
        party_id,
        converted,
    )
    if not e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Party update failed. {str(e)}",
        )


@router.delete(
    "/party/{party_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(is_owner)],
)
async def delete_party(request: Request, party_id: str):
    e = await delete_party_instance(party_id)
    if not e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Party deletion failed. {str(e)}",
        )


@router.put("/party/{party_id}/users", status_code=status.HTTP_204_NO_CONTENT)
async def add_user_to_party(request: Request, party_id: str):
    try:
        userid = decode_jwt(request.cookies["session"])["user_id"]
        _id = ObjectId(userid)
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user id.",
        )
    party = await get_party_instance(party_id)
    if not party:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Party not found."
        )
    if party["party_info"]["type"] == "private":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unauthorized. Party is private.",
        )

    e = await update_party_instance(party_id, {"party_info.users": _id}, "$addToSet")
    if not e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Party update failed. {str(e)}",
        )
