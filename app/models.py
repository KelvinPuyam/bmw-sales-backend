from sqlalchemy import Column, Integer, String, Numeric, SmallInteger, BigInteger, Date, Enum
from sqlalchemy.sql import func
from sqlalchemy import DateTime
import enum
from database import Base


class RoleEnum(str, enum.Enum):
    admin = "admin"
    user = "user"


class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    username   = Column(String(50), unique=True, nullable=False, index=True)
    email      = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name  = Column(String(100), nullable=False)
    phone      = Column(String(20), nullable=True)
    dob        = Column(Date, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role       = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.user)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SalesFact(Base):
    __tablename__ = "sales_fact"

    id               = Column(Integer, primary_key=True, index=True)
    year             = Column(SmallInteger, nullable=False)
    month            = Column(SmallInteger, nullable=False)
    region           = Column(String(50), nullable=False)
    model            = Column(String(50), nullable=False)
    units_sold       = Column(Integer, nullable=False)
    avg_price_eur    = Column(Numeric(12, 2), nullable=False)
    revenue_eur      = Column(BigInteger, nullable=False)
    bev_share        = Column(Numeric(6, 4), nullable=False)
    premium_share    = Column(Numeric(6, 4), nullable=False)
    gdp_growth       = Column(Numeric(6, 4), nullable=False)
    fuel_price_index = Column(Numeric(6, 4), nullable=False)
