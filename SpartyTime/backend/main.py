import uvicorn
from fastapi import FastAPI
from routes import auth, parties
from utils.database_handler import close_db, delete_parties, open_db
from utils.party_handler import (
    add_new_parties,
    check_for_inactivity,
    update_party_details,
    update_playback,
)
from utils.spotify_handler import close_session, create_session


app = FastAPI()

routers = [auth.router, parties.router]
for router in routers:
    app.include_router(router)


app.add_event_handler("startup", open_db)
app.add_event_handler("startup", create_session)
app.add_event_handler("startup", add_new_parties)
app.add_event_handler("startup", check_for_inactivity)
app.add_event_handler("startup", update_party_details)
app.add_event_handler("startup", update_playback)

app.add_event_handler("shutdown", delete_parties)
app.add_event_handler("shutdown", close_db)
app.add_event_handler("shutdown", close_session)


if __name__ == "__main__":

    uvicorn.run("main:app", reload=True)
