from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from app.db_models.users import User_db
from app.models import User
from app.db_session_provider import get_db
from uuid import UUID
from app.dependencies import check_admin_role, get_api_key

router = APIRouter(prefix="/api/v1/admin/user", tags=["user", "admin"])


@router.delete("/{user_id}", responses={200: {"model": User}})
async def delete_user(
        user_id: UUID,
        api_key: str = Depends(get_api_key),
        user: User_db = Depends(check_admin_role),
        db: AsyncSession = Depends(get_db)
):
    user_result = await db.execute(
        select(User_db).where(User_db.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.execute(
        delete(User_db).where(User_db.id == user_id)
    )

    await db.commit()

    return user
