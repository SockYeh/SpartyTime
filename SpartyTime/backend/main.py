import os, aiohttp
from contextlib import asynccontextmanager

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .routes import auth, discovery, parties
from .utils.database_handler import (
    close_db,
    create_party_db,
    create_user_db,
    delete_parties,
    open_db,
    get_party_instance,
    get_party_user_pfps,
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

    await delete_parties()
    await close_db()
    await close_session()  # pyright: ignore


app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=os.environ["SECRET"])
templates = Jinja2Templates(directory=r"spartytime\frontend")
app.mount(
    "/static", StaticFiles(directory=r"spartytime\frontend\assets"), name="static"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


routers = [auth.router, parties.router, discovery.router]
for router in routers:
    app.include_router(router)


# @app.get("/")
# async def create_dbs():
#     await create_user_db()
#     await create_party_db()

#     return {"message": "Databases created"}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    async with aiohttp.ClientSession() as session:
        if request.session.get("user_id"):
            print(request.session.get("user_id"))
            async with session.get(
                str(request.url_for("match_genres")), headers=request.headers
            ) as resp:
                parties = await resp.json()
        else:
            async with session.get(str(request.url_for("get_all_parties"))) as resp:
                print(resp.status)
                parties = await resp.json()
    print(parties)
    print(type(parties))
    return templates.TemplateResponse(
        "index.html", {"request": request, "parties": parties["parties"][:5]}
    )


@app.get("/party/{party_id}", response_class=HTMLResponse)
async def party(request: Request, party_id: str):
    try:
        party = await get_party_instance(party_id)
        pfps = await get_party_user_pfps(party_id)
        if request.session.get("user_id"):
            users = [str(i) for i in party.party_info.users] + [
                str(party.party_info.owner)
            ]
            is_member = request.session["user_id"] in users
    except Exception:
        return RedirectResponse(
            str(request.url_for("home")), status_code=status.HTTP_404_NOT_FOUND
        )
    return templates.TemplateResponse(
        "party-info.html",
        {
            "request": request,
            "party": party.model_dump(),
            "pfps": pfps,
            "is_member": is_member,
        },
    )
