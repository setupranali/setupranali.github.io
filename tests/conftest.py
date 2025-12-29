"""
Pytest configuration and shared fixtures for SetuPranali tests.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def api_key():
    """Return a valid test API key."""
    return "dev-key-123"


@pytest.fixture
def tenant_a_key():
    """Return API key for tenant A."""
    return "tenantA-key"


@pytest.fixture
def tenant_b_key():
    """Return API key for tenant B."""
    return "tenantB-key"


@pytest.fixture
def sample_query():
    """Return a sample query payload."""
    return {
        "dataset": "orders",
        "dimensions": [{"name": "city"}],
        "metrics": [{"name": "total_revenue"}]
    }

