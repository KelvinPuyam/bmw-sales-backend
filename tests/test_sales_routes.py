"""
Integration tests for /sales/* endpoints.
All endpoints require authentication; we use auth_headers() to generate
a valid JWT without needing a real user in the session-scoped DB.
"""

import pytest
from tests.conftest import auth_headers

AUTH = auth_headers("salesuser", role="user")


class TestSalesSummary:
    def test_requires_auth(self, client):
        resp = client.get("/sales/summary")
        assert resp.status_code == 401

    def test_returns_list(self, client):
        resp = client.get("/sales/summary", headers=AUTH)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_response_shape(self, client):
        resp = client.get("/sales/summary", headers=AUTH)
        for row in resp.json():
            assert "year" in row
            assert "total_units" in row
            assert "total_revenue" in row
            assert "avg_bev_share" in row


class TestByRegion:
    def test_returns_list(self, client):
        resp = client.get("/sales/by-region", headers=AUTH)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_year_filter_query_param(self, client):
        resp = client.get("/sales/by-region?year=2022", headers=AUTH)
        assert resp.status_code == 200
        for row in resp.json():
            assert row["year"] == 2022

    def test_invalid_year_param_returns_422(self, client):
        resp = client.get("/sales/by-region?year=notanumber", headers=AUTH)
        assert resp.status_code == 422


class TestByModel:
    def test_returns_list(self, client):
        resp = client.get("/sales/by-model", headers=AUTH)
        assert resp.status_code == 200

    def test_year_filter_works(self, client):
        resp = client.get("/sales/by-model?year=2023", headers=AUTH)
        assert resp.status_code == 200
        for row in resp.json():
            assert row["year"] == 2023


class TestByYear:
    def test_returns_list(self, client):
        resp = client.get("/sales/by-year", headers=AUTH)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_all_years_empty_when_no_data(self, client):
        resp = client.get("/sales/by-year", headers=AUTH)
        assert resp.status_code == 200
        # Route DB has no sales data seeded, so result is empty
        assert resp.json() == []

    def test_specific_year_filter(self, client):
        resp = client.get("/sales/by-year?year=2022", headers=AUTH)
        assert resp.status_code == 200

    def test_combined_filters(self, client):
        resp = client.get("/sales/by-year?year=2022&region=Europe", headers=AUTH)
        assert resp.status_code == 200

    def test_invalid_year_param_returns_422(self, client):
        resp = client.get("/sales/by-year?year=notanumber", headers=AUTH)
        assert resp.status_code == 422


class TestMonthlyTrend:
    def test_returns_list(self, client):
        resp = client.get("/sales/monthly-trend", headers=AUTH)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_row_has_month_field(self, client):
        resp = client.get("/sales/monthly-trend", headers=AUTH)
        for row in resp.json():
            assert "month" in row
            assert 1 <= row["month"] <= 12


class TestBevTrend:
    def test_returns_list(self, client):
        resp = client.get("/sales/bev-trend", headers=AUTH)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_bev_share_in_range(self, client):
        resp = client.get("/sales/bev-trend", headers=AUTH)
        for row in resp.json():
            assert 0.0 <= row["avg_bev_share"] <= 1.0


class TestRawSales:
    def test_returns_paginated_response(self, client):
        resp = client.get("/sales/raw", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "results" in data

    def test_default_page_is_1(self, client):
        resp = client.get("/sales/raw", headers=AUTH)
        assert resp.json()["page"] == 1

    def test_custom_page_size(self, client):
        resp = client.get("/sales/raw?size=2", headers=AUTH)
        assert resp.json()["size"] == 2

    def test_size_above_max_returns_422(self, client):
        resp = client.get("/sales/raw?size=9999", headers=AUTH)
        assert resp.status_code == 422

    def test_page_zero_returns_422(self, client):
        resp = client.get("/sales/raw?page=0", headers=AUTH)
        assert resp.status_code == 422

    def test_filter_by_year(self, client):
        resp = client.get("/sales/raw?year=2022", headers=AUTH)
        assert resp.status_code == 200
        for row in resp.json()["results"]:
            assert row["year"] == 2022


class TestFilterOptions:
    def test_returns_years_regions_models(self, client):
        resp = client.get("/sales/filters", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "years" in data
        assert "regions" in data
        assert "models" in data

    def test_years_is_list(self, client):
        resp = client.get("/sales/filters", headers=AUTH)
        assert isinstance(resp.json()["years"], list)

    def test_requires_auth(self, client):
        resp = client.get("/sales/filters")
        assert resp.status_code == 401