import json
import random
from typing import Optional

import redis
from sqlalchemy import func, cast, Float
from sqlalchemy.orm import Session

from app import models, schemas
from app.logger import get_logger

logger = get_logger(__name__)

# ── Redis ─────────────────────────────────────────────────────────────────────

CACHE_VERSION = "v1"

_redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True,
)


def _get_cached(key: str):
    try:
        data = _redis_client.get(key)
        if data:
            logger.debug("Cache HIT: %s", key)
            return json.loads(data)
    except Exception as exc:
        logger.warning("Cache GET failed for key '%s': %s", key, exc)
    return None


def _set_cached(key: str, value, ttl: int = 300) -> None:
    try:
        jittered_ttl = ttl + random.randint(0, 60)

        if isinstance(value, list):
            serialisable = [
                v.model_dump() if hasattr(v, "model_dump") else v for v in value
            ]
        elif hasattr(value, "model_dump"):
            serialisable = value.model_dump()
        else:
            serialisable = value

        _redis_client.setex(key, jittered_ttl, json.dumps(serialisable))
        logger.debug("Cache SET: %s (ttl=%ds)", key, jittered_ttl)
    except Exception as exc:
        logger.warning("Cache SET failed for key '%s': %s", key, exc)


# ── 1. Annual summary ─────────────────────────────────────────────────────────

def get_annual_summary(db: Session) -> list[schemas.SummaryRow]:
    """
    Total units, revenue, avg price, avg BEV share and avg GDP growth
    grouped by year.
    """
    key = f"{CACHE_VERSION}:summary"
    if cached := _get_cached(key):
        return cached

    logger.info("DB query: annual_summary")
    try:
        rows = (
            db.query(
                models.SalesFact.year,
                func.sum(models.SalesFact.units_sold)                       .label("total_units"),
                func.sum(models.SalesFact.revenue_eur)                      .label("total_revenue"),
                func.avg(cast(models.SalesFact.avg_price_eur, Float))       .label("avg_price_eur"),
                func.avg(cast(models.SalesFact.bev_share, Float))           .label("avg_bev_share"),
                func.avg(cast(models.SalesFact.gdp_growth, Float))          .label("avg_gdp_growth"),
            )
            .group_by(models.SalesFact.year)
            .order_by(models.SalesFact.year)
            .all()
        )
    except Exception as exc:
        logger.exception("DB error in annual_summary: %s", exc)
        raise

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

    _set_cached(key, result, ttl=600)
    return result


# ── 2. By region × year ───────────────────────────────────────────────────────

def get_by_region(
    db: Session,
    year: Optional[int] = None,
) -> list[schemas.RegionRow]:
    """Units, revenue, avg price, avg BEV share per region per year."""
    logger.info("DB query: by_region year=%s", year)
    try:
        q = db.query(
            models.SalesFact.region,
            models.SalesFact.year,
            func.sum(models.SalesFact.units_sold)                    .label("total_units"),
            func.sum(models.SalesFact.revenue_eur)                   .label("total_revenue"),
            func.avg(cast(models.SalesFact.avg_price_eur, Float))    .label("avg_price_eur"),
            func.avg(cast(models.SalesFact.bev_share, Float))        .label("avg_bev_share"),
        ).group_by(models.SalesFact.region, models.SalesFact.year)

        if year:
            q = q.filter(models.SalesFact.year == year)

        rows = q.order_by(models.SalesFact.year, models.SalesFact.region).all()
    except Exception as exc:
        logger.exception("DB error in by_region (year=%s): %s", year, exc)
        raise

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

def get_by_model(
    db: Session,
    year: Optional[int] = None,
) -> list[schemas.ModelRow]:
    """Units, revenue, avg price per model per year."""
    key = f"{CACHE_VERSION}:by-model:{year or 'all'}"
    if cached := _get_cached(key):
        return cached

    logger.info("DB query: by_model year=%s", year)
    try:
        q = db.query(
            models.SalesFact.model,
            models.SalesFact.year,
            func.sum(models.SalesFact.units_sold)                    .label("total_units"),
            func.sum(models.SalesFact.revenue_eur)                   .label("total_revenue"),
            func.avg(cast(models.SalesFact.avg_price_eur, Float))    .label("avg_price_eur"),
        ).group_by(models.SalesFact.model, models.SalesFact.year)

        if year:
            q = q.filter(models.SalesFact.year == year)

        rows = q.order_by(models.SalesFact.year, models.SalesFact.model).all()
    except Exception as exc:
        logger.exception("DB error in by_model (year=%s): %s", year, exc)
        raise

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

    _set_cached(key, result, ttl=300)
    return result


# ── 4. By year (aggregated, with optional filters) ────────────────────────────

def get_by_year(
    db: Session,
    year: Optional[int]   = None,
    region: Optional[str] = None,
    model: Optional[str]  = None,
) -> list[schemas.SummaryRow]:
    """
    Annual totals with optional region/model filter.
    Returns one row per matching year, or a single aggregated row when no year filter.
    """
    key = f"{CACHE_VERSION}:by-year:{year or 'all'}:{region or 'all'}:{model or 'all'}"
    if cached := _get_cached(key):
        return cached

    logger.info("DB query: by_year year=%s region=%s model=%s", year, region, model)

    try:
        if year:
            q = db.query(
                models.SalesFact.year,
                func.sum(models.SalesFact.units_sold)                 .label("total_units"),
                func.sum(models.SalesFact.revenue_eur)                .label("total_revenue"),
                func.avg(cast(models.SalesFact.avg_price_eur, Float)) .label("avg_price_eur"),
                func.avg(cast(models.SalesFact.bev_share, Float))     .label("avg_bev_share"),
                func.avg(cast(models.SalesFact.gdp_growth, Float))    .label("avg_gdp_growth"),
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
        else:
            # Aggregate across all years
            agg = db.query(
                func.sum(models.SalesFact.units_sold)                 .label("total_units"),
                func.sum(models.SalesFact.revenue_eur)                .label("total_revenue"),
                func.avg(cast(models.SalesFact.avg_price_eur, Float)) .label("avg_price_eur"),
                func.avg(cast(models.SalesFact.bev_share, Float))     .label("avg_bev_share"),
                func.avg(cast(models.SalesFact.gdp_growth, Float))    .label("avg_gdp_growth"),
            )
            if region:
                agg = agg.filter(models.SalesFact.region == region)
            if model:
                agg = agg.filter(models.SalesFact.model == model)

            r = agg.one()
            result = [
                schemas.SummaryRow(
                    year           = 0,   # sentinel: 0 = "All Years"
                    total_units    = r.total_units,
                    total_revenue  = float(r.total_revenue),
                    avg_price_eur  = round(float(r.avg_price_eur), 2),
                    avg_bev_share  = round(float(r.avg_bev_share), 4),
                    avg_gdp_growth = round(float(r.avg_gdp_growth), 4),
                )
            ]
    except Exception as exc:
        logger.exception("DB error in by_year (year=%s region=%s model=%s): %s", year, region, model, exc)
        raise

    _set_cached(key, result, ttl=300)
    return result


# ── 5. Monthly trend ──────────────────────────────────────────────────────────

def get_monthly_trend(
    db: Session,
    year: Optional[int] = None,
) -> list[schemas.MonthlyTrendRow]:
    """Global units and revenue per year+month."""
    logger.info("DB query: monthly_trend year=%s", year)
    try:
        q = db.query(
            models.SalesFact.year,
            models.SalesFact.month,
            func.sum(models.SalesFact.units_sold)                     .label("total_units"),
            func.sum(models.SalesFact.revenue_eur)                    .label("total_revenue"),
            func.avg(cast(models.SalesFact.bev_share, Float))         .label("avg_bev_share"),
            func.avg(cast(models.SalesFact.fuel_price_index, Float))  .label("avg_fuel_price"),
        ).group_by(models.SalesFact.year, models.SalesFact.month)

        if year:
            q = q.filter(models.SalesFact.year == year)

        rows = q.order_by(models.SalesFact.year, models.SalesFact.month).all()
    except Exception as exc:
        logger.exception("DB error in monthly_trend (year=%s): %s", year, exc)
        raise

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

def get_bev_trend(db: Session) -> list[schemas.BevTrendRow]:
    """Average BEV share per region per year."""
    logger.info("DB query: bev_trend")
    try:
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
    except Exception as exc:
        logger.exception("DB error in bev_trend: %s", exc)
        raise

    return [
        schemas.BevTrendRow(
            region        = r.region,
            year          = r.year,
            avg_bev_share = round(float(r.avg_bev_share), 4),
        )
        for r in rows
    ]


# ── 7. Raw data (paginated) ───────────────────────────────────────────────────

def get_raw_sales(
    db: Session,
    page: int,
    size: int,
    year: Optional[int]   = None,
    region: Optional[str] = None,
    model: Optional[str]  = None,
) -> schemas.PaginatedSales:
    """Paginated raw fact table."""
    logger.info("DB query: raw_sales page=%d size=%d year=%s region=%s model=%s", page, size, year, region, model)
    try:
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
    except Exception as exc:
        logger.exception("DB error in raw_sales: %s", exc)
        raise

    return schemas.PaginatedSales(
        total   = total,
        page    = page,
        size    = size,
        results = [schemas.RawSalesRow.model_validate(r) for r in rows],
    )


# ── 8. Filter options ─────────────────────────────────────────────────────────

def get_filter_options(db: Session) -> dict:
    """Distinct years, regions and models for populating filter dropdowns."""
    
    key = f"{CACHE_VERSION}:filter-options"
    if cached := _get_cached(key):
        return cached

    logger.info("DB query: filter_options")

    try:
        years = [
            r[0]
            for r in db.query(models.SalesFact.year)
            .distinct()
            .order_by(models.SalesFact.year)
            .all()
        ]

        regions = [
            r[0]
            for r in db.query(models.SalesFact.region)
            .distinct()
            .order_by(models.SalesFact.region)
            .all()
        ]

        model_list = [
            r[0]
            for r in db.query(models.SalesFact.model)
            .distinct()
            .order_by(models.SalesFact.model)
            .all()
        ]

        result = {
            "years": years,
            "regions": regions,
            "models": model_list,
        }

    except Exception as exc:
        logger.exception("DB error in filter_options: %s", exc)
        raise

    _set_cached(key, result, ttl=3600)
    return result
