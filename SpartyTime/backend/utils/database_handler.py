import asyncio
import os

from dotenv import find_dotenv, load_dotenv
from email_validator import EmailNotValidError, validate_email
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import errors
from bson.errors import InvalidId
from bson.objectid import ObjectId
import pydantic


load_dotenv(find_dotenv())

password = os.getenv("mongodb_password")
connection_str = f"mongodb+srv://SockYeh:{password}@spartytime.ym3qwwl.mongodb.net/?retryWrites=true&w=majority&authSource=admin"
client = None


async def open_db():
    global client, users_db, parties_db
    client = AsyncIOMotorClient(connection_str)  # type ignore
    users_db = client.users
    parties_db = client.parties


async def close_db():
    client.close()  # pyright: ignore


def convert_to_bson_id(bson_id: str) -> ObjectId:

    return ObjectId(bson_id)


class SpotifySessionModel(pydantic.BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    scope: str
    refresh_token: str
    expires_at: int


class UserModel(pydantic.BaseModel):
    _id: ObjectId
    username: str
    genres: list[str]
    spotify_id: str
    spotify_data: dict
    spotify_session_data: SpotifySessionModel
    current_party_id: str

    @pydantic.validator("_id", pre=True, always=True)
    def check_id(cls, value):
        if not ObjectId.is_valid(value):
            raise InvalidId(f"{value} is not a valid ObjectId. ")
        return value


async def create_user_db():
    await client.drop_database("users")  # pyright: ignore
    auth_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["username", "spotify_id", "spotify_data"],
            "properties": {
                "username": {
                    "bsonType": "string",
                    "description": "must be a string. Spotify username of the user",
                },
                "genres": {
                    "bsonType": "array",
                    "description": "must be an array. List of genres for the user",
                },
                "spotify_id": {
                    "bsonType": "string",
                    "description": "must be a string. Spotify ID of the user",
                },
                "spotify_data": {
                    "bsonType": "object",
                    "description": "must be an object. Spotify data of the user",
                },
                "spotify_session_data": {
                    "bsonType": "object",
                    "description": "must be an object. Spotify session data of the user",
                },
                "current_party_id": {
                    "bsonType": "string",
                    "description": "must be a string. ID of the party the user is currently in",
                },
            },
        },
    }

    try:
        await users_db.create_collection("auth_details")
    except Exception as e:
        print(e)

    await users_db.command("collMod", "auth_details", validator=auth_validator)

    await users_db.auth_details.create_index("username", unique=True)
    await users_db.auth_details.create_index("spotify_id", unique=True)


class PartyInfoModel(pydantic.BaseModel):
    party_name: str
    party_description: str
    genres: list[str]
    start: int
    users: list[ObjectId]
    owner: str
    type: str

    @pydantic.validator("owner", pre=True, always=True)
    def check_owner(cls, value):
        if not ObjectId.is_valid(value):
            raise InvalidId(f"{value} is not a valid ObjectId. ")
        return value

    @pydantic.validator("users", pre=True, always=True)
    def check_users(cls, value):
        for user in value:
            if not ObjectId.is_valid(user):
                raise InvalidId(f"{user} is not a valid ObjectId. ")
        return value

    @pydantic.validator("type", pre=True, always=True)
    def check_type(cls, value):
        if value not in ["public", "unlisted", "private"]:
            raise ValueError(f"{value} is not a valid party type. ")
        return value


class PartyDataModel(pydantic.BaseModel):
    is_playing: bool
    current_song: dict
    time_since_last_played: int
    queue: list[dict]
    history: list[dict]


class PartyModel(pydantic.BaseModel):
    _id: ObjectId
    party_info: PartyInfoModel
    party_data: PartyDataModel | None

    @pydantic.validator("_id", pre=True, always=True)
    def check_id(cls, value):
        if not ObjectId.is_valid(value):
            raise InvalidId(f"{value} is not a valid ObjectId. ")
        return value


async def create_party_db():
    await client.drop_database("parties")  # pyright: ignore

    party_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["party_info"],
            "properties": {
                "party_info": {
                    "bsonType": "object",
                    "description": "must be an object",
                    "items": {
                        "bsonType": "object",
                        "required": [
                            "party_name",
                            "party_description",
                            "start",
                            "users",
                            "owner",
                            "type",
                        ],
                        "properties": {
                            "party_name": {
                                "bsonType": "string",
                                "description": "must be a string. Name of the party",
                            },
                            "party_description": {
                                "bsonType": "string",
                                "description": "must be a string. Description of the party",
                            },
                            "genres": {
                                "bsonType": "array",
                                "description": "must be an array. List of genres for the party",
                            },
                            "start": {
                                "bsonType": "int",
                                "description": "must be an int. Start time (in ms)",
                            },
                            "users": {
                                "bsonType": "array",
                                "description": "must be an array. List of user ids in the party ",
                                "items": {"bsonType": "string"},
                            },
                            "owner": {
                                "bsonType": "string",
                                "description": "must be a string. ID of the owner of the party",
                            },
                            "type": {
                                "bsonType": "string",
                                "description": "must be a string. Type of the party",
                                "enum": ["public", "unlisted", "private"],
                            },
                        },
                    },
                },
                "party_data": {
                    "bsonType": "object",
                    "description": "must be an object",
                    "items": {
                        "bsonType": "object",
                        "properties": {
                            "is_playing": {
                                "bsonType": "bool",
                                "description": "must be a bool. Whether the song is playing",
                            },
                            "current_song": {
                                "bsonType": "object",
                                "description": "must be an object. Current song playing in the party",
                            },
                            "time_since_last_played": {
                                "bsonType": "int",
                                "description": "must be an int. Time since the last song stopped playing",
                            },
                            "queue": {
                                "bsonType": "array",
                                "description": "must be an array. List of songs in the queue",
                            },
                            "history": {
                                "bsonType": "array",
                                "description": "must be an array. List of songs played in the party",
                            },
                        },
                    },
                },
            },
        },
    }

    try:
        await parties_db.create_collection("party_details")
    except Exception as e:
        print(e)

    await parties_db.command("collMod", "party_details", validator=party_validator)


async def get_user_by_id(_id: str, is_spotify_id=False) -> UserModel:
    query = {"spotify_id": _id} if is_spotify_id else {"_id": convert_to_bson_id(_id)}
    op = await users_db.auth_details.find_one(query)
    if not op:
        raise ValueError(f"User with id {_id} not found. ")
    return UserModel(**op)


async def create_user(spotify_dict: dict, spotify_session_dict: dict) -> bool:
    try:
        username = spotify_dict["display_name"]
        user_id = spotify_dict["id"]
        await users_db.auth_details.insert_one(
            {
                "username": username,
                "spotify_id": user_id,
                "spotify_data": spotify_dict,
                "spotify_session_data": spotify_session_dict,
            }
        )
        return True
    except errors.DuplicateKeyError:
        return False


async def update_session(user_id: str, session_data: dict) -> bool:
    try:
        e = await users_db.auth_details.update_one(
            {"_id": convert_to_bson_id(user_id)},
            {"$set": {"spotify_session_data": session_data}},
        )
        return True
    except Exception:
        return False


async def update_user(user_id: str, user_data: dict) -> bool:
    try:
        e = await users_db.auth_details.update_one(
            {"_id": convert_to_bson_id(user_id)},
            {"$set": user_data},
        )
        return True
    except Exception:
        return False


async def get_user_by_access_token(access_token: str) -> UserModel:
    query = {"spotify_session_data.access_token": access_token}
    op = await users_db.auth_details.find_one(query)

    if not op:
        raise ValueError(f"User with access token {access_token} not found. ")
    return UserModel(**op)


async def create_party_instance(party: dict):
    e = await parties_db.party_details.insert_one(party)
    return e.inserted_id


async def get_party_instance(party_id: str) -> PartyModel:
    query = {"_id": convert_to_bson_id(party_id)}
    op = await parties_db.party_details.find_one(query)

    if not op:
        raise ValueError(f"Party with id {party_id} not found")
    return PartyModel(**op)


async def get_party_instance_by_owner(owner_id: str) -> PartyModel:
    query = {"party_info.owner": owner_id}
    op = await parties_db.party_details.find_one(query)

    if not op:
        raise ValueError(f"Party with owner id {owner_id} not found. ")

    return PartyModel(**op)


async def update_party_instance(
    party_id: str, party: dict, method: str = "$set"
) -> bool:
    try:
        del party["_id"]
    except KeyError:
        pass
    await parties_db.party_details.update_one(
        {"_id": convert_to_bson_id(party_id)}, {method: party}
    )
    return True


async def remove_party_member(party_id: str, user_id: str) -> bool:
    await parties_db.party_details.update_one(
        {"_id": convert_to_bson_id(party_id)}, {"$pull": {"party_info.users": user_id}}
    )
    await users_db.auth_details.update_one(
        {"_id": convert_to_bson_id(user_id)}, {"$set": {"current_party_id": "None"}}
    )
    return True


async def delete_party_instance(party_id: str) -> bool:
    await parties_db.party_details.delete_one({"_id": convert_to_bson_id(party_id)})
    return True


async def get_parties(filter_dict: dict = {}) -> list:
    op = parties_db.party_details.find(filter_dict)
    return [PartyModel(**i) async for i in op]


async def delete_parties() -> bool:
    await parties_db.party_details.delete_many({})
    return True


async def get_users(filter_dict: dict = {}) -> list:
    op = users_db.auth_details.find(filter_dict)
    return [UserModel(**i) async for i in op]


async def aggregate_party(filter_dict: list) -> list:
    op = parties_db.party_details.aggregate(filter_dict)
    return [PartyModel(**i) async for i in op]
