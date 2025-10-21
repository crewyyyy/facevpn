from database.models import User, VpnProfile
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


async def get_vpn_profile_by_user_id(user_id: int) -> Optional[VpnProfile]:
    async with async_session() as session:
        result = await session.execute(
            select(VpnProfile).where(VpnProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()


async def get_vpn_profile_by_tg(tg_id: int) -> Optional[VpnProfile]:
    async with async_session() as session:
        result = await session.execute(
            select(VpnProfile).join(User).where(User.tg_id == tg_id)
        )
        return result.scalar_one_or_none()


async def save_vpn_profile(
    *,
    user_id: int,
    uuid: str,
    label: str,
    server: str,
    port: int,
    transport: str,
    security: str,
    flow: Optional[str] = None,
    sni: Optional[str] = None,
    path: Optional[str] = None,
    remote_id: Optional[str] = None,
    last_synced_at: Optional[datetime] = None,
    last_sync_error: Optional[str] = None,
) -> VpnProfile:
    async with async_session() as session:
        result = await session.execute(
            select(VpnProfile).where(VpnProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        now = datetime.utcnow()
        if profile is None:
            profile = VpnProfile(
                user_id=user_id,
                uuid=uuid,
                label=label,
                server=server,
                port=port,
                transport=transport,
                security=security,
                flow=flow,
                sni=sni,
                path=path,
                remote_id=remote_id,
                last_synced_at=last_synced_at,
                last_sync_error=last_sync_error,
                created_at=now,
                updated_at=now,
            )
            session.add(profile)
        else:
            profile.uuid = uuid
            profile.label = label
            profile.server = server
            profile.port = port
            profile.transport = transport
            profile.security = security
            profile.flow = flow
            profile.sni = sni
            profile.path = path
            if remote_id is not None or profile.remote_id is None:
                profile.remote_id = remote_id
            profile.last_synced_at = last_synced_at
            profile.last_sync_error = last_sync_error
            profile.updated_at = now

        await session.commit()
        await session.refresh(profile)
        return profile
