from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine
from app.routers import auth, users, sales

# Create tables that don't exist yet (only users — sales_fact was created by ETL)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BMW Sales Dashboard API",
    version="1.0.0",
    description="REST API for BMW global sales analytics with JWT authentication.",
)

# Allow the React dev server to call this API during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(sales.router)


@app.get("/")
def root():
    return {"message": "BMW Sales API is running"}
