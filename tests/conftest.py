"""
Shared pytest fixtures for the BMW Sales Backend test suite.

Strategy:
- Unit/service tests (test_*_service.py, test_schemas.py, test_security.py):
  Each test gets its own fresh SQLite file-based DB via the `db` fixture.
- Integration/route tests (test_*_routes.py):
  The `client` fixture uses a single persistent SQLite file so all requests
  within a test class share state (signup then login).
- Redis is replaced by an in-memory FakeRedis for all tests.
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# ── Fake Redis ────────────────────────────────────────────────────────────────

class FakeRedis:
    """Thread-safe in-memory drop-in for redis.Redis."""

    def __init__(self):
        self._store: dict = {}

    def get(self, key: str):
        return self._store.get(key)

    def setex(self, key: str, ttl: int, value):
        self._store[key] = value

    def delete(self, key: str):
        self._store.pop(key, None)

    def flushall(self):
        self._store.clear()


# ── Patch Redis before any app module is loaded ───────────────────────────────

@pytest.fixture(scope="session")
def fake_redis():
    return FakeRedis()


@pytest.fixture(scope="session", autouse=True)
def patch_redis(fake_redis):
    import app.services.sales_service as sales_svc
    original = sales_svc._redis_client
    sales_svc._redis_client = fake_redis
    yield fake_redis
    sales_svc._redis_client = original


# ── Per-test DB (for service/unit tests) ─────────────────────────────────────

@pytest.fixture()
def db():
    """
    Yields a fresh SQLAlchemy session backed by a temporary SQLite file.
    The file (and all its data) is deleted after the test.
    """
    from database import Base

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    url = f"sqlite:///{path}"
    test_engine = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        test_engine.dispose()
        os.unlink(path)


# ── Persistent DB + client (for route/integration tests) ─────────────────────

@pytest.fixture(scope="session")
def _route_db_path(tmp_path_factory):
    """A single SQLite file shared across all route tests in the session."""
    return str(tmp_path_factory.mktemp("route_db") / "route_test.db")


@pytest.fixture(scope="session")
def _route_engine(_route_db_path):
    from database import Base
    eng = create_engine(
        f"sqlite:///{_route_db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture(scope="session")
def app(_route_engine, patch_redis):
    from main import app as fastapi_app
    from app.deps import get_db, get_current_user, get_admin_user
    from app import models
    from app.exceptions.base import ForbiddenError

    RouteSession = sessionmaker(autocommit=False, autoflush=False, bind=_route_engine)

    def override_get_db():
        db = RouteSession()
        try:
            yield db
        finally:
            db.close()

    import fastapi as _fa
    import fastapi.security as _fas
    _oauth2 = _fas.OAuth2PasswordBearer(tokenUrl="/auth/token")

    # By depending on the *original* get_db, FastAPI de-duplicates the session
    # so the User object returned here is bound to the same Session the route
    # handler receives — enabling db.refresh / db.commit to work correctly.
    def override_get_current_user(
        token: str = _fa.Depends(_oauth2),
        db=_fa.Depends(get_db),
    ):
        """Validate JWT; use real DB user if present, else return a synthetic user."""
        from app.security import decode_access_token
        from jose import JWTError
        from app.exceptions.base import InvalidTokenError
        try:
            payload = decode_access_token(token)
            username = payload.get("sub")
            role_str = payload.get("role", "user")
            if not username:
                raise InvalidTokenError()
        except JWTError:
            raise InvalidTokenError()
        real_user = db.query(models.User).filter(models.User.username == username).first()
        if real_user:
            return real_user
        from datetime import datetime, timezone
        return models.User(
            id=0,
            username=username,
            email=f"{username}@test.local",
            first_name="Test",
            last_name="User",
            hashed_password="",
            role=models.RoleEnum(role_str),
            created_at=datetime.now(timezone.utc),
        )

    def override_get_admin_user(current_user: models.User = __import__("fastapi").Depends(override_get_current_user)):
        if current_user.role != models.RoleEnum.admin:
            raise ForbiddenError()
        return current_user

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_current_user] = override_get_current_user
    fastapi_app.dependency_overrides[get_admin_user] = override_get_admin_user
    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    return TestClient(app)


# ── Seed fixtures (for per-test db) ──────────────────────────────────────────

@pytest.fixture()
def seed_user(db):
    """Creates a plain 'user' role account; returns (user_obj, raw_password)."""
    from app.models import User, RoleEnum
    from app.security import hash_password

    password = "testpass1"
    user = User(
        username="testuser",
        email="testuser@example.com",
        first_name="Test",
        last_name="User",
        hashed_password=hash_password(password),
        role=RoleEnum.user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, password


@pytest.fixture()
def seed_admin(db):
    """Creates an admin account; returns (user_obj, raw_password)."""
    from app.models import User, RoleEnum
    from app.security import hash_password

    password = "adminpass1"
    admin = User(
        username="adminuser",
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        hashed_password=hash_password(password),
        role=RoleEnum.admin,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin, password


@pytest.fixture()
def seed_sales(db):
    """Inserts a handful of SalesFact rows for query tests."""
    from app.models import SalesFact

    rows = [
        SalesFact(year=2022, month=1,  region="Europe",       model="3 Series", units_sold=500,  avg_price_eur=40000, revenue_eur=20_000_000, bev_share=0.15, premium_share=0.30, gdp_growth=0.02,  fuel_price_index=1.1),
        SalesFact(year=2022, month=2,  region="Europe",       model="5 Series", units_sold=300,  avg_price_eur=55000, revenue_eur=16_500_000, bev_share=0.20, premium_share=0.50, gdp_growth=0.02,  fuel_price_index=1.1),
        SalesFact(year=2022, month=1,  region="Asia Pacific", model="X5",       units_sold=800,  avg_price_eur=70000, revenue_eur=56_000_000, bev_share=0.30, premium_share=0.60, gdp_growth=0.05,  fuel_price_index=0.9),
        SalesFact(year=2023, month=3,  region="Europe",       model="i4",       units_sold=1000, avg_price_eur=65000, revenue_eur=65_000_000, bev_share=0.80, premium_share=0.70, gdp_growth=0.03,  fuel_price_index=1.2),
        SalesFact(year=2023, month=6,  region="Americas",     model="X3",       units_sold=600,  avg_price_eur=50000, revenue_eur=30_000_000, bev_share=0.10, premium_share=0.40, gdp_growth=0.025, fuel_price_index=1.0),
    ]
    db.add_all(rows)
    db.commit()
    return rows


# ── Token helpers ─────────────────────────────────────────────────────────────

def get_token_for(username: str, role: str) -> str:
    from app.security import create_access_token
    return create_access_token({"sub": username, "role": role})


def auth_headers(username: str, role: str = "user") -> dict:
    return {"Authorization": f"Bearer {get_token_for(username, role)}"}