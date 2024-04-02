from fastapi import HTTPException, Request


async def validate_session(request: Request):
    """Validates the session of the user."""
    try:
        request.session["user_id"]
    except KeyError:
        raise HTTPException(status_code=401, detail="Invalid Session!")
