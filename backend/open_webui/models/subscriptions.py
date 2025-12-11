import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from open_webui.internal.db import Base, get_db


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_name = Column(String(120), unique=True, nullable=False)
    tokens_per_seat = Column(Integer, nullable=False, default=0)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Client(Base):
    __tablename__ = "client"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), unique=True, nullable=False)
    subscription_plan_id = Column(
        Integer, ForeignKey("subscription_plan.id"), nullable=True
    )
    seats_purchased = Column(Integer, nullable=False, default=1)
    next_reset_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    subscription_plan = relationship("SubscriptionPlan")
    users = relationship("UsagePerUser", back_populates="client")


class UsagePerUser(Base):
    __tablename__ = "usage_per_user"
    __table_args__ = (UniqueConstraint("user_id", name="uq_usage_per_user_user_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("user.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("client.id"), nullable=True)
    used_tokens = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    client = relationship("Client", back_populates="users")


class SubscriptionPlanModel(BaseModel):
    id: int
    plan_name: str
    tokens_per_seat: int
    description: Optional[str] = None
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ClientModel(BaseModel):
    id: int
    name: str
    subscription_plan_id: Optional[int] = None
    seats_purchased: int
    next_reset_date: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class UsagePerUserModel(BaseModel):
    id: int
    user_id: str
    client_id: Optional[int] = None
    used_tokens: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriptionPlansTable:
    @staticmethod
    def get_plan_by_id(plan_id: int) -> Optional[SubscriptionPlanModel]:
        with get_db() as db:
            plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
            return SubscriptionPlanModel.model_validate(plan) if plan else None


class ClientsTable:
    @staticmethod
    def get_client_by_id(client_id: int) -> Optional[ClientModel]:
        with get_db() as db:
            client = db.query(Client).filter(Client.id == client_id).first()
            return ClientModel.model_validate(client) if client else None


class UsagePerUserTable:
    @staticmethod
    def get_or_create_usage(user_id: str, client_id: Optional[int] = None) -> UsagePerUserModel:
        with get_db() as db:
            usage = db.query(UsagePerUser).filter(UsagePerUser.user_id == user_id).first()
            if not usage:
                usage = UsagePerUser(user_id=user_id, client_id=client_id, used_tokens=0)
                db.add(usage)
                db.commit()
                db.refresh(usage)
            return UsagePerUserModel.model_validate(usage)


