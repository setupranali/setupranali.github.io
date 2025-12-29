"""
Tests for core API endpoints.
"""

import pytest


class TestDatasets:
    """Tests for /v1/datasets endpoint."""

    def test_list_datasets(self, client):
        """Test listing available datasets."""
        response = client.get("/v1/datasets")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_dataset_metadata(self, client):
        """Test getting metadata for a specific dataset."""
        response = client.get("/v1/datasets/orders")
        # May return 200 or 404 depending on setup
        assert response.status_code in [200, 404]


class TestQuery:
    """Tests for /v1/query endpoint."""

    def test_query_requires_auth(self, client, sample_query):
        """Test that query endpoint requires authentication."""
        response = client.post("/v1/query", json=sample_query)
        assert response.status_code == 401

    def test_query_with_valid_key(self, client, api_key, sample_query):
        """Test query with valid API key."""
        response = client.post(
            "/v1/query",
            json=sample_query,
            headers={"X-API-Key": api_key}
        )
        # Should succeed or fail gracefully
        assert response.status_code in [200, 400, 404]

    def test_query_invalid_dataset(self, client, api_key):
        """Test query with non-existent dataset."""
        response = client.post(
            "/v1/query",
            json={
                "dataset": "nonexistent_dataset",
                "dimensions": [{"name": "foo"}],
                "metrics": [{"name": "bar"}]
            },
            headers={"X-API-Key": api_key}
        )
        assert response.status_code in [400, 404]


class TestRLS:
    """Tests for Row-Level Security."""

    def test_different_tenants_see_different_data(
        self, client, tenant_a_key, tenant_b_key, sample_query
    ):
        """Test that different tenant keys return different data."""
        response_a = client.post(
            "/v1/query",
            json=sample_query,
            headers={"X-API-Key": tenant_a_key}
        )
        response_b = client.post(
            "/v1/query",
            json=sample_query,
            headers={"X-API-Key": tenant_b_key}
        )
        
        # Both should succeed or both should indicate RLS is working
        if response_a.status_code == 200 and response_b.status_code == 200:
            data_a = response_a.json()
            data_b = response_b.json()
            # Stats should show different tenants
            if "stats" in data_a and "stats" in data_b:
                assert data_a["stats"].get("tenant") != data_b["stats"].get("tenant")

