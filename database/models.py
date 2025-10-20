from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, ForeignKey, String, Float
from sqlalchemy.ext.asyncio import AsyncAttrs
from datetime import datetime

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(128), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="ru")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    balance: Mapped[float] = mapped_column(Float, default=0.0)

    referrer_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    referrals_count: Mapped[int] = mapped_column(Integer, default=0)