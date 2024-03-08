import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

from routes import auth, parties, discovery
from utils.database_handler import close_db, delete_parties, open_db
from utils.party_handler import (
    add_new_parties,
    check_for_inactivity,
    update_party_details,
    update_playback,
    update_party_genre,
)
from utils.spotify_handler import close_session, create_session, update_user_genre


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
    await close_session()


app = FastAPI(lifespan=lifespan)

routers = [auth.router, parties.router, discovery.router]
for router in routers:
    app.include_router(router)


if __name__ == "__main__":

    uvicorn.run("main:app", reload=True)
