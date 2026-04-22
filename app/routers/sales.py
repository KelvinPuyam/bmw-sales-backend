from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Float

from app import models, schemas
from app.deps import get_db, get_current_user

import redis
import json
import random

router = APIRouter(prefix="/sales", tags=["Sales"])

# Every endpoint requires a valid JWT — no admin needed, any logged-in user can read.
AuthDep = Depends(get_current_user)

# Redis connection
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True
)

CACHE_VERSION = "v1"

def get_cached(key: str):
    try:
        data = redis_client.get(key)
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None


def set_cached(key: str, value, ttl: int = 300):
    try:
        ttl = ttl + random.randint(0, 60)

        # convert pydantic models → dict
        if isinstance(value, list):
            value = [
                v.model_dump() if hasattr(v, "model_dump") else v
                for v in value
            ]
        elif hasattr(value, "model_dump"):
            value = value.model_dump()

        redis_client.setex(key, ttl, json.dumps(value))

    except Exception:
        pass


# ── 1. Annual summary ─────────────────────────────────────────────────────────

@router.get("/summary", response_model=list[schemas.SummaryRow])
def annual_summary(db: Session = Depends(get_db), _=AuthDep):
    """
    Total units, total revenue, avg price, avg BEV share and avg GDP growth
    grouped by year — powers the KPI cards and the annual bar chart.
    """
    key = f"{CACHE_VERSION}:summary"

    if cached := get_cached(key):
        return cached

    rows = (
        db.query(
            models.SalesFact.year,
            func.sum(models.SalesFact.units_sold)                        .label("total_units"),
            func.sum(models.SalesFact.revenue_eur)                       .label("total_revenue"),
            func.avg(cast(models.SalesFact.avg_price_eur, Float))        .label("avg_price_eur"),
            func.avg(cast(models.SalesFact.bev_share, Float))            .label("avg_bev_share"),
            func.avg(cast(models.SalesFact.gdp_growth, Float))           .label("avg_gdp_growth"),
        )
        .group_by(models.SalesFact.year)
        .order_by(models.SalesFact.year)
        .all()
    )

    result = [
        schemas.SummaryRow(
            year           = r.year,
            total_units    = r.total_units,
            total_revenue  = float(r.total_revenue),
            avg_price_eur  = round(float(r.avg_price_eur), 2),
            avg_bev_share  = round(float(r.avg_bev_share), 4),
            avg_gdp_growth = round(float(r.avg_gdp_growth), 4),
        )
        for r in rows
    ]

    set_cached(key, result, ttl=600)

    return result


# ── 2. By region × year ────────────────────────────────────────────────────────

@router.get("/by-region", response_model=list[schemas.RegionRow])
def by_region(
    year: int | None = Query(None, description="Filter by a specific year"),
    db: Session = Depends(get_db),
    _=AuthDep,
):
    """
    Units, revenue, avg price, avg BEV share per region per year.
    Powers the regional comparison chart.
    """
    q = db.query(
        models.SalesFact.region,
        models.SalesFact.year,
        func.sum(models.SalesFact.units_sold)                     .label("total_units"),
        func.sum(models.SalesFact.revenue_eur)                    .label("total_revenue"),
        func.avg(cast(models.SalesFact.avg_price_eur, Float))     .label("avg_price_eur"),
        func.avg(cast(models.SalesFact.bev_share, Float))         .label("avg_bev_share"),
    ).group_by(models.SalesFact.region, models.SalesFact.year)

    if year:
        q = q.filter(models.SalesFact.year == year)

    rows = q.order_by(models.SalesFact.year, models.SalesFact.region).all()
    return [
        schemas.RegionRow(
            region        = r.region,
            year          = r.year,
            total_units   = r.total_units,
            total_revenue = float(r.total_revenue),
            avg_price_eur = round(float(r.avg_price_eur), 2),
            avg_bev_share = round(float(r.avg_bev_share), 4),
        )
        for r in rows
    ]


# ── 3. By model × year ────────────────────────────────────────────────────────

@router.get("/by-model", response_model=list[schemas.ModelRow])
def by_model(
    year: int | None = Query(None, description="Filter by a specific year"),
    db: Session = Depends(get_db),
    _=AuthDep,
):
    """
    Units, revenue, avg price per model per year.
    Powers the model performance table.
    """
    key = f"{CACHE_VERSION}:by-model:{year or 'all'}"

    if cached := get_cached(key):
        return cached

    q = db.query(
        models.SalesFact.model,
        models.SalesFact.year,
        func.sum(models.SalesFact.units_sold)                     .label("total_units"),
        func.sum(models.SalesFact.revenue_eur)                    .label("total_revenue"),
        func.avg(cast(models.SalesFact.avg_price_eur, Float))     .label("avg_price_eur"),
    ).group_by(models.SalesFact.model, models.SalesFact.year)

    if year:
        q = q.filter(models.SalesFact.year == year)

    rows = q.order_by(models.SalesFact.year, models.SalesFact.model).all()

    result = [
        schemas.ModelRow(
            model         = r.model,
            year          = r.year,
            total_units   = r.total_units,
            total_revenue = float(r.total_revenue),
            avg_price_eur = round(float(r.avg_price_eur), 2),
        )
        for r in rows
    ]

    set_cached(key, result, ttl=300)

    return result


# ── 4. By year only (all regions + models combined) ──────────────────────────

@router.get("/by-year", response_model=list[schemas.SummaryRow])
def by_year(
    year:   int | None = Query(None, description="Filter by year"),
    region: str | None = Query(None, description="Filter by region"),
    model:  str | None = Query(None, description="Filter by model"),
    db: Session = Depends(get_db),
    _=AuthDep,
):
    """
    Annual totals with optional region/model filter.
    When a specific year is provided, returns that year's row.
    When no year is provided, returns a single aggregated row across all years.
    """
    key = f"{CACHE_VERSION}:by-year:{year or 'all'}:{region or 'all'}:{model or 'all'}"

    if cached := get_cached(key):
        return cached

    # ── Specific year requested → return that year's row ──
    if year:
        q = db.query(
            models.SalesFact.year,
            func.sum(models.SalesFact.units_sold)                  .label("total_units"),
            func.sum(models.SalesFact.revenue_eur)                 .label("total_revenue"),
            func.avg(cast(models.SalesFact.avg_price_eur, Float))  .label("avg_price_eur"),
            func.avg(cast(models.SalesFact.bev_share, Float))      .label("avg_bev_share"),
            func.avg(cast(models.SalesFact.gdp_growth, Float))     .label("avg_gdp_growth"),
        ).group_by(models.SalesFact.year).filter(models.SalesFact.year == year)

        if region:
            q = q.filter(models.SalesFact.region == region)
        if model:
            q = q.filter(models.SalesFact.model == model)

        rows = q.order_by(models.SalesFact.year).all()

        result = [
            schemas.SummaryRow(
                year           = r.year,
                total_units    = r.total_units,
                total_revenue  = float(r.total_revenue),
                avg_price_eur  = round(float(r.avg_price_eur), 2),
                avg_bev_share  = round(float(r.avg_bev_share), 4),
                avg_gdp_growth = round(float(r.avg_gdp_growth), 4),
            )
            for r in rows
        ]

        set_cached(key, result, ttl=300)

        return result

    # ── No year filter → return one aggregated "All Years" row ──
    agg = db.query(
        func.sum(models.SalesFact.units_sold)                  .label("total_units"),
        func.sum(models.SalesFact.revenue_eur)                 .label("total_revenue"),
        func.avg(cast(models.SalesFact.avg_price_eur, Float))  .label("avg_price_eur"),
        func.avg(cast(models.SalesFact.bev_share, Float))      .label("avg_bev_share"),
        func.avg(cast(models.SalesFact.gdp_growth, Float))     .label("avg_gdp_growth"),
    )

    if region:
        agg = agg.filter(models.SalesFact.region == region)
    if model:
        agg = agg.filter(models.SalesFact.model == model)

    r = agg.one()

    result = [
        schemas.SummaryRow(
            year           = 0,  # sentinel value — 0 means "All Years"
            total_units    = r.total_units,
            total_revenue  = float(r.total_revenue),
            avg_price_eur  = round(float(r.avg_price_eur), 2),
            avg_bev_share  = round(float(r.avg_bev_share), 4),
            avg_gdp_growth = round(float(r.avg_gdp_growth), 4),
        )
    ]

    set_cached(key, result, ttl=300)

    return result


# ── 5. Monthly trend ──────────────────────────────────────────────────────────

@router.get("/monthly-trend", response_model=list[schemas.MonthlyTrendRow])
def monthly_trend(
    year: int | None = Query(None, description="Filter by a specific year"),
    db: Session = Depends(get_db),
    _=AuthDep,
):
    """
    Global units and revenue per year+month.
    Powers the monthly line chart.
    """
    q = db.query(
        models.SalesFact.year,
        models.SalesFact.month,
        func.sum(models.SalesFact.units_sold)                      .label("total_units"),
        func.sum(models.SalesFact.revenue_eur)                     .label("total_revenue"),
        func.avg(cast(models.SalesFact.bev_share, Float))          .label("avg_bev_share"),
        func.avg(cast(models.SalesFact.fuel_price_index, Float))   .label("avg_fuel_price"),
    ).group_by(models.SalesFact.year, models.SalesFact.month)

    if year:
        q = q.filter(models.SalesFact.year == year)

    rows = q.order_by(models.SalesFact.year, models.SalesFact.month).all()
    return [
        schemas.MonthlyTrendRow(
            year           = r.year,
            month          = r.month,
            total_units    = r.total_units,
            total_revenue  = float(r.total_revenue),
            avg_bev_share  = round(float(r.avg_bev_share), 4),
            avg_fuel_price = round(float(r.avg_fuel_price), 4),
        )
        for r in rows
    ]


# ── 6. BEV adoption trend ─────────────────────────────────────────────────────

@router.get("/bev-trend", response_model=list[schemas.BevTrendRow])
def bev_trend(db: Session = Depends(get_db), _=AuthDep):
    """
    Average BEV share per region per year.
    Powers the EV adoption line chart.
    """
    rows = (
        db.query(
            models.SalesFact.region,
            models.SalesFact.year,
            func.avg(cast(models.SalesFact.bev_share, Float)).label("avg_bev_share"),
        )
        .group_by(models.SalesFact.region, models.SalesFact.year)
        .order_by(models.SalesFact.region, models.SalesFact.year)
        .all()
    )
    return [
        schemas.BevTrendRow(
            region        = r.region,
            year          = r.year,
            avg_bev_share = round(float(r.avg_bev_share), 4),
        )
        for r in rows
    ]


# ── 7. Raw data (paginated) ───────────────────────────────────────────────────

@router.get("/raw", response_model=schemas.PaginatedSales)
def raw_sales(
    page:   int         = Query(1,    ge=1,  description="Page number"),
    size:   int         = Query(50,   ge=1, le=200, description="Rows per page"),
    year:   int | None  = Query(None, description="Filter by year"),
    region: str | None  = Query(None, description="Filter by region"),
    model:  str | None  = Query(None, description="Filter by model"),
    db: Session = Depends(get_db),
    _=AuthDep,
):
    """
    Paginated raw fact table — useful for a detailed data view page.
    """
    q = db.query(models.SalesFact)

    if year:
        q = q.filter(models.SalesFact.year == year)
    if region:
        q = q.filter(models.SalesFact.region == region)
    if model:
        q = q.filter(models.SalesFact.model == model)

    total = q.count()
    rows  = q.order_by(
        models.SalesFact.year,
        models.SalesFact.month,
        models.SalesFact.region,
        models.SalesFact.model,
    ).offset((page - 1) * size).limit(size).all()

    return schemas.PaginatedSales(
        total=total, page=page, size=size,
        results=[schemas.RawSalesRow.model_validate(r) for r in rows],
    )


# ── 8. Filter options ─────────────────────────────────────────────────────────

@router.get("/filters")
def filter_options(db: Session = Depends(get_db), _=AuthDep):
    """
    Returns the distinct years, regions and models available.
    Frontend uses this to populate filter dropdowns.
    """
    years      = [r[0] for r in db.query(models.SalesFact.year)  .distinct().order_by(models.SalesFact.year).all()]
    regions    = [r[0] for r in db.query(models.SalesFact.region).distinct().order_by(models.SalesFact.region).all()]
    model_list = [r[0] for r in db.query(models.SalesFact.model) .distinct().order_by(models.SalesFact.model).all()]
    return {"years": years, "regions": regions, "models": model_list}
