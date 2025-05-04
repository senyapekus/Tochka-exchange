from fastapi import HTTPException, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db_models.users import User_db
from app.db_session_provider import get_db

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def get_api_key(api_key: str = Depends(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=401, detail="Authorization header is required")

    if not api_key.startswith("TOKEN "):
        raise HTTPException(status_code=401, detail="Invalid API key format. Expected 'TOKEN <api_key>'")

    return api_key.replace("TOKEN ", "").strip()


async def get_user(api_key: str = Depends(get_api_key), db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(
        select(User_db).where(User_db.api_key == api_key))

    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


async def check_admin_role(user: User_db = Depends(get_user)):
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Access denied. Admin role required")

    return user
