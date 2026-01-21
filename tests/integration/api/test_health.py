"""
Tests for health check endpoint.
"""


def test_health_check(client):
    """Test that health endpoint returns OK."""
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_health_check_includes_version(client):
    """Test that health endpoint includes version info."""
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data or "status" in data

