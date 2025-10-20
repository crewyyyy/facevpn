from database.models import User
from database.session import async_session
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import Tuple, Optional


async def create_user(
    tg_id: int,
    username: str = None,
    full_name: str = None,
    ref_code: int = None
) -> Tuple[User, Optional[int]]:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            return user, None

        referrer = None
        if ref_code and ref_code != tg_id:
            ref_result = await session.execute(select(User).where(User.tg_id == ref_code))
            referrer = ref_result.scalar_one_or_none()

        user = User(
            tg_id=tg_id,
            username=username,
            full_name=full_name,
            referrer_id=referrer.id if referrer else None
        )
        session.add(user)

        referrer_tg_id = None
        if referrer:
            referrer.referrals_count += 1
            referrer.is_premium = True
            now = datetime.utcnow()
            if not referrer.premium_until or referrer.premium_until < now:
                referrer.premium_until = now + timedelta(days=7)
            else:
                referrer.premium_until += timedelta(days=7)
            referrer_tg_id = referrer.tg_id

        await session.commit()
        await session.refresh(user)
        return user, referrer_tg_id

async def extend_premium(user_id: int, days: int):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False

        now = datetime.utcnow()
        if not user.premium_until or user.premium_until < now:
            user.premium_until = now + timedelta(days=days)
        else:
            user.premium_until += timedelta(days=days)

        user.is_premium = True
        await session.commit()
        return True

async def add_balance(user_id: int, amount: float):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False
        user.balance += amount
        await session.commit()
        return True

async def spend_balance(user_id: int, amount: float):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == user_id))
        user = result.scalar_one_or_none()
        if not user or user.balance < amount:
            return False
        user.balance -= amount
        await session.commit()
        return True

async def get_user_by_username(username: str):
    if username.startswith("@"):
        username = username[1:]
    async with async_session() as session:
        result = await session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

async def get_user_by_tg(tg_id: int):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        return result.scalar_one_or_none()
