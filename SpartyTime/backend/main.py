import os
from contextlib import asynccontextmanager

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from .routes import auth, discovery, parties
from .utils.database_handler import (
    close_db,
    create_party_db,
    create_user_db,
    delete_parties,
    open_db,
)
from .utils.party_handler import (
    add_new_parties,
    check_for_inactivity,
    update_party_details,
    update_party_genre,
    update_playback,
)
from .utils.spotify_handler import close_session, create_session, update_user_genre

load_dotenv(find_dotenv())


@asynccontextmanager
async def lifespan(app: FastAPI):

    await open_db()
    await create_session()
    await add_new_parties()
    await check_for_inactivity()
    await update_party_details()
    await update_playback()
    await update_user_genre(all=True)
    await update_party_genre()
    yield

    # await delete_parties()
    await close_db()
    await close_session()  # pyright: ignore


app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=os.environ["SECRET"])

routers = [auth.router, parties.router, discovery.router]
for router in routers:
    app.include_router(router)


@app.get("/")
async def create_dbs():
    await create_user_db()
    await create_party_db()

    return {"message": "Databases created"}
