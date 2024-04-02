import logging
import time
from typing import Optional

import pydantic
from bson.errors import InvalidId
from bson.objectid import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..utils.database_handler import (
    PartyInfoModel,
    create_party_instance,
    delete_party_instance,
    get_party_instance,
    update_party_instance,
)
from ..utils.logger_handler import LoggerFormatter
from ..utils.session_manager import validate_session

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(LoggerFormatter())
logger.addHandler(stream_handler)

router = APIRouter(
    prefix="/parties", tags=["parties"], dependencies=[Depends(validate_session)]
)


class Party(BaseModel):
    party_name: str
    party_description: Optional[str] = "This is a party."
    users: Optional[list[str]] = []
    type: str

    @pydantic.field_validator("type")
    @classmethod
    def check_type(cls, value):
        if value not in ["public", "unlisted", "private"]:
            raise ValueError(f"{value} is not a valid party type. ")
        return value


class UpdateParty(BaseModel):
    party_name: Optional[str] = None
    party_description: Optional[str] = None
    owner: Optional[str] = None
    type: Optional[str] = None


async def is_owner(request: Request, party_id: str) -> bool:
    """Dependency to check if the user is the owner of the party."""
    userid = request.session["user_id"]
    e = await get_party_instance(party_id)
    if not e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Party not found. {str(e)}"
        )
    if e.party_info.owner != userid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Unauthorized. {str(e)}"
        )
    return True


@router.post("/party", status_code=status.HTTP_201_CREATED)
async def create_party(request: Request, payload: Party) -> JSONResponse:
    """API endpoint to create a party"""
    userid = request.session["user_id"]
    party_info = PartyInfoModel(
        **payload.model_dump(), owner=userid, start=round(time.time())
    )

    e = await create_party_instance({"party_info": party_info.model_dump()})
    if not e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Party creation failed. {str(e)}",
        )
    logger.info(f"Party {e} created")
    return JSONResponse(content={"id": str(e)})


@router.get(
    "/party/{party_id}",
    status_code=status.HTTP_200_OK,
)
async def get_party(request: Request, party_id: str) -> JSONResponse:
    """API endpoint to get a party by id"""
    e = await get_party_instance(party_id)
    if not e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Party not found. {str(e)}"
        )
    opd = e.model_dump()
    opd["id"] = str(e.id)
    opd["party_info"]["owner"] = str(opd["party_info"]["owner"])
    opd["party_info"]["users"] = [str(i) for i in opd["party_info"]["users"]]

    return JSONResponse(content={"party": opd})


@router.patch(
    "/party/{party_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(is_owner)],
)
async def update_party(request: Request, party_id: str, payload: UpdateParty) -> None:
    """API endpoint to update a party by id"""
    converted = payload.model_dump(exclude_unset=True)

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
async def delete_party(request: Request, party_id: str) -> None:
    """API endpoint to delete a party by id"""
    e = await delete_party_instance(party_id)
    if not e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Party deletion failed. {str(e)}",
        )
    logger.info(f"Party {party_id} deleted.")


@router.put("/party/{party_id}/users", status_code=status.HTTP_204_NO_CONTENT)
async def add_user_to_party(request: Request, party_id: str) -> None:
    """API endpoint to add a user to a party"""
    try:
        userid = request.session["user_id"]
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
    if party.party_info.type == "private":
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
