import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.user_repository import create_user, get_user_by_email
from app.models.user import User
from app.services.jwt import create_access_token
from app.services.password import hash_password, verify_password


async def register_user(session: AsyncSession, email: str, password: str) -> User:
    normalized_email = email.lower()
    existing_user = await get_user_by_email(session, normalized_email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered.",
        )

    user_id = str(uuid.uuid4())
    hashed = hash_password(password)
    return await create_user(session, user_id=user_id, email=normalized_email, hashed_password=hashed)


async def login_user(session: AsyncSession, email: str, password: str) -> str:
    normalized_email = email.lower()
    user = await get_user_by_email(session, normalized_email)
    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    return create_access_token(user.id)
