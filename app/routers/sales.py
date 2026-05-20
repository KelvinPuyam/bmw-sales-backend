from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import schemas
from app.deps import get_db, get_current_user
from app.services import sales_service

router = APIRouter(prefix="/sales", tags=["Sales"])

# Every endpoint requires a valid JWT — no admin needed, any logged-in user can read.
AuthDep = Depends(get_current_user)


# ── 1. Annual summary ─────────────────────────────────────────────────────────

@router.get("/summary", response_model=list[schemas.SummaryRow])
def annual_summary(db: Session = Depends(get_db), _=AuthDep):
    """
    Total units, total revenue, avg price, avg BEV share and avg GDP growth
    grouped by year — powers the KPI cards and the annual bar chart.
    """
    return sales_service.get_annual_summary(db)


# ── 2. By region × year ───────────────────────────────────────────────────────

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
    return sales_service.get_by_region(db, year=year)


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
    return sales_service.get_by_model(db, year=year)


# ── 4. By year (aggregated, with optional filters) ────────────────────────────

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
    return sales_service.get_by_year(db, year=year, region=region, model=model)


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
    return sales_service.get_monthly_trend(db, year=year)


# ── 6. BEV adoption trend ─────────────────────────────────────────────────────

@router.get("/bev-trend", response_model=list[schemas.BevTrendRow])
def bev_trend(db: Session = Depends(get_db), _=AuthDep):
    """
    Average BEV share per region per year.
    Powers the EV adoption line chart.
    """
    return sales_service.get_bev_trend(db)


# ── 7. Raw data (paginated) ───────────────────────────────────────────────────

@router.get("/raw", response_model=schemas.PaginatedSales)
def raw_sales(
    page:   int        = Query(1,    ge=1,         description="Page number"),
    size:   int        = Query(50,   ge=1, le=200, description="Rows per page"),
    year:   int | None = Query(None,               description="Filter by year"),
    region: str | None = Query(None,               description="Filter by region"),
    model:  str | None = Query(None,               description="Filter by model"),
    db: Session = Depends(get_db),
    _=AuthDep,
):
    """
    Paginated raw fact table — useful for a detailed data view page.
    """
    return sales_service.get_raw_sales(db, page=page, size=size, year=year, region=region, model=model)


# ── 8. Filter options ─────────────────────────────────────────────────────────

@router.get("/filters")
def filter_options(db: Session = Depends(get_db), _=AuthDep):
    """
    Returns the distinct years, regions and models available.
    Frontend uses this to populate filter dropdowns.
    """
    return sales_service.get_filter_options(db)
