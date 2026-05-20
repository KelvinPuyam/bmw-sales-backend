from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from database import Base, engine
from app.routers import auth, users, sales
from app.exceptions.base import AppException
from app.logger import get_logger

logger = get_logger(__name__)

# Create tables that don't exist yet (only users — sales_fact was created by ETL)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BMW Sales Dashboard API",
    version="1.0.0",
    description="REST API for BMW global sales analytics with JWT authentication.",
)

# ── Global exception handlers ─────────────────────────────────────────────────

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Converts every domain exception into a consistent JSON error envelope."""
    logger.warning(
        "AppException [%d] on %s %s — %s",
        exc.status_code, request.method, request.url.path, exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all for any unexpected errors — logs full traceback, returns 500."""
    logger.exception(
        "Unhandled exception on %s %s: %s",
        request.method, request.url.path, exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://bmw-sales-frontend.vercel.app", "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(sales.router)


@app.get("/")
def root():
    return {"message": "BMW Sales API is running"}
