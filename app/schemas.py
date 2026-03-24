from pydantic import BaseModel, EmailStr, field_validator
from datetime import date, datetime
from typing import Optional
from app.models import RoleEnum


# ── Auth ────────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    username:   str
    password:   str
    first_name: str
    last_name:  str
    email:      EmailStr
    phone:      Optional[str] = None
    dob:        Optional[date] = None

    @field_validator("username")
    @classmethod
    def username_no_spaces(cls, v: str) -> str:
        if " " in v:
            raise ValueError("Username must not contain spaces")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"


# ── User ─────────────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id:         int
    username:   str
    email:      str
    first_name: str
    last_name:  str
    phone:      Optional[str]
    dob:        Optional[date]
    role:       RoleEnum
    created_at: datetime

    model_config = {"from_attributes": True}


class AssignRoleRequest(BaseModel):
    role: RoleEnum


# ── Sales summary ─────────────────────────────────────────────────────────────

class SummaryRow(BaseModel):
    year:             int
    total_units:      int
    total_revenue:    float
    avg_price_eur:    float
    avg_bev_share:    float
    avg_gdp_growth:   float

    model_config = {"from_attributes": True}


class RegionRow(BaseModel):
    region:        str
    year:          int
    total_units:   int
    total_revenue: float
    avg_price_eur: float
    avg_bev_share: float

    model_config = {"from_attributes": True}


class ModelRow(BaseModel):
    model:         str
    year:          int
    total_units:   int
    total_revenue: float
    avg_price_eur: float

    model_config = {"from_attributes": True}


class MonthlyTrendRow(BaseModel):
    year:          int
    month:         int
    total_units:   int
    total_revenue: float
    avg_bev_share: float
    avg_fuel_price: float

    model_config = {"from_attributes": True}


class BevTrendRow(BaseModel):
    region:        str
    year:          int
    avg_bev_share: float

    model_config = {"from_attributes": True}


class RawSalesRow(BaseModel):
    id:               int
    year:             int
    month:            int
    region:           str
    model:            str
    units_sold:       int
    avg_price_eur:    float
    revenue_eur:      float
    bev_share:        float
    premium_share:    float
    gdp_growth:       float
    fuel_price_index: float

    model_config = {"from_attributes": True}


class PaginatedSales(BaseModel):
    total:   int
    page:    int
    size:    int
    results: list[RawSalesRow]
