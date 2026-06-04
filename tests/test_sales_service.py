"""
Unit tests for app/services/sales_service.py
Uses seed_sales fixture for DB rows; Redis is replaced by FakeRedis.
"""

import pytest


class TestGetAnnualSummary:
    def test_returns_list(self, db, seed_sales, fake_redis):
        fake_redis.flushall()
        from app.services.sales_service import get_annual_summary
        result = get_annual_summary(db)
        assert isinstance(result, list)

    def test_groups_by_year(self, db, seed_sales, fake_redis):
        fake_redis.flushall()
        from app.services.sales_service import get_annual_summary
        result = get_annual_summary(db)
        years = [r["year"] if isinstance(r, dict) else r.year for r in result]
        assert sorted(set(years)) == sorted(years), "years should be unique and sorted"
        assert 2022 in years
        assert 2023 in years

    def test_empty_db_returns_empty_list(self, db, fake_redis):
        fake_redis.flushall()
        from app.services.sales_service import get_annual_summary
        result = get_annual_summary(db)
        assert result == []

    def test_result_is_cached_on_second_call(self, db, seed_sales, fake_redis):
        fake_redis.flushall()
        from app.services.sales_service import get_annual_summary
        first = get_annual_summary(db)
        second = get_annual_summary(db)
        # Both calls should return the same data
        assert len(first) == len(second)


class TestGetByRegion:
    def test_returns_all_regions_when_no_year(self, db, seed_sales):
        from app.services.sales_service import get_by_region
        result = get_by_region(db)
        regions = {r.region for r in result}
        assert "Europe" in regions
        assert "Asia Pacific" in regions

    def test_filters_by_year(self, db, seed_sales):
        from app.services.sales_service import get_by_region
        result = get_by_region(db, year=2023)
        years = {r.year for r in result}
        assert years == {2023}

    def test_unknown_year_returns_empty(self, db, seed_sales):
        from app.services.sales_service import get_by_region
        result = get_by_region(db, year=1999)
        assert result == []

    def test_revenue_is_float(self, db, seed_sales):
        from app.services.sales_service import get_by_region
        result = get_by_region(db)
        for row in result:
            assert isinstance(row.total_revenue, float)


class TestGetByModel:
    def test_returns_rows(self, db, seed_sales, fake_redis):
        fake_redis.flushall()
        from app.services.sales_service import get_by_model
        result = get_by_model(db)
        assert len(result) > 0

    def test_filters_by_year(self, db, seed_sales, fake_redis):
        fake_redis.flushall()
        from app.services.sales_service import get_by_model
        result = get_by_model(db, year=2022)
        years = {r.year for r in result}
        assert years == {2022}

    def test_model_names_present(self, db, seed_sales, fake_redis):
        fake_redis.flushall()
        from app.services.sales_service import get_by_model
        result = get_by_model(db)
        model_names = {r.model for r in result}
        assert "3 Series" in model_names


class TestGetByYear:
    def test_specific_year_returns_one_row(self, db, seed_sales, fake_redis):
        fake_redis.flushall()
        from app.services.sales_service import get_by_year
        result = get_by_year(db, year=2022)
        assert len(result) == 1
        assert result[0].year == 2022

    def test_no_year_returns_sentinel_zero(self, db, seed_sales, fake_redis):
        fake_redis.flushall()
        from app.services.sales_service import get_by_year
        result = get_by_year(db)
        assert len(result) == 1
        assert result[0].year == 0  # sentinel for "all years"

    def test_empty_db_returns_empty_list(self, db, fake_redis):
        fake_redis.flushall()
        from app.services.sales_service import get_by_year
        result = get_by_year(db)
        assert result == []

    def test_filter_by_region(self, db, seed_sales, fake_redis):
        fake_redis.flushall()
        from app.services.sales_service import get_by_year
        result = get_by_year(db, year=2022, region="Europe")
        # Europe in 2022 has 2 rows (3 Series + 5 Series) → 1 aggregated result
        assert len(result) == 1
        assert result[0].total_units == 800  # 500 + 300

    def test_unknown_year_returns_empty(self, db, seed_sales, fake_redis):
        fake_redis.flushall()
        from app.services.sales_service import get_by_year
        result = get_by_year(db, year=1900)
        assert result == []


class TestGetMonthlyTrend:
    def test_returns_rows(self, db, seed_sales):
        from app.services.sales_service import get_monthly_trend
        result = get_monthly_trend(db)
        assert len(result) > 0

    def test_filters_by_year(self, db, seed_sales):
        from app.services.sales_service import get_monthly_trend
        result = get_monthly_trend(db, year=2023)
        years = {r.year for r in result}
        assert years == {2023}

    def test_row_fields(self, db, seed_sales):
        from app.services.sales_service import get_monthly_trend
        result = get_monthly_trend(db)
        row = result[0]
        assert hasattr(row, "year")
        assert hasattr(row, "month")
        assert hasattr(row, "total_units")
        assert hasattr(row, "avg_bev_share")


class TestGetBevTrend:
    def test_returns_rows(self, db, seed_sales):
        from app.services.sales_service import get_bev_trend
        result = get_bev_trend(db)
        assert len(result) > 0

    def test_bev_share_is_float(self, db, seed_sales):
        from app.services.sales_service import get_bev_trend
        result = get_bev_trend(db)
        for row in result:
            assert isinstance(row.avg_bev_share, float)
            assert 0.0 <= row.avg_bev_share <= 1.0


class TestGetRawSales:
    def test_pagination_page1(self, db, seed_sales):
        from app.services.sales_service import get_raw_sales
        result = get_raw_sales(db, page=1, size=3)
        assert result.page == 1
        assert result.size == 3
        assert len(result.results) == 3
        assert result.total == 5

    def test_pagination_page2(self, db, seed_sales):
        from app.services.sales_service import get_raw_sales
        result = get_raw_sales(db, page=2, size=3)
        assert len(result.results) == 2  # only 2 rows left

    def test_filter_by_year(self, db, seed_sales):
        from app.services.sales_service import get_raw_sales
        result = get_raw_sales(db, page=1, size=50, year=2022)
        assert result.total == 3
        for row in result.results:
            assert row.year == 2022

    def test_filter_by_region(self, db, seed_sales):
        from app.services.sales_service import get_raw_sales
        result = get_raw_sales(db, page=1, size=50, region="Europe")
        for row in result.results:
            assert row.region == "Europe"

    def test_filter_by_model(self, db, seed_sales):
        from app.services.sales_service import get_raw_sales
        result = get_raw_sales(db, page=1, size=50, model="X5")
        assert result.total == 1
        assert result.results[0].model == "X5"


class TestGetFilterOptions:
    def test_returns_years_regions_models(self, db, seed_sales, fake_redis):
        fake_redis.flushall()
        from app.services.sales_service import get_filter_options
        result = get_filter_options(db)
        assert "years" in result
        assert "regions" in result
        assert "models" in result

    def test_years_sorted(self, db, seed_sales, fake_redis):
        fake_redis.flushall()
        from app.services.sales_service import get_filter_options
        result = get_filter_options(db)
        assert result["years"] == sorted(result["years"])

    def test_correct_distinct_values(self, db, seed_sales, fake_redis):
        fake_redis.flushall()
        from app.services.sales_service import get_filter_options
        result = get_filter_options(db)
        assert set(result["years"]) == {2022, 2023}
        assert "Europe" in result["regions"]
        assert "i4" in result["models"]