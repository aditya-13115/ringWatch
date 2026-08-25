from fastapi.testclient import TestClient

from backend.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_ready():
    with TestClient(app) as client:
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json()["data_store_initialized"] is True


def test_queue():
    with TestClient(app) as client:
        response = client.get("/api/queue")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 7
        assert len(data["accounts"]) == 7


def test_account_detail_valid():
    with TestClient(app) as client:
        queue_response = client.get("/api/queue")
        assert queue_response.status_code == 200

        accounts = queue_response.json()["accounts"]
        assert len(accounts) > 0

        account_id = accounts[0]["account_id"]

        response = client.get(f"/api/accounts/{account_id}")
        assert response.status_code == 200
        assert response.json()["account_id"] == account_id


def test_account_detail_not_found():
    with TestClient(app) as client:
        response = client.get("/api/accounts/UNKNOWN")
        assert response.status_code == 404


def test_graph_valid():
    with TestClient(app) as client:
        response = client.get("/api/accounts/A000529/graph")
        assert response.status_code == 200
        assert "nodes" in response.json()
        assert "edges" in response.json()


def test_evidence_valid():
    with TestClient(app) as client:
        response = client.get("/api/accounts/A000529/evidence")
        assert response.status_code == 200
        assert "fields" in response.json()


def test_report_valid():
    with TestClient(app) as client:
        response = client.get("/api/accounts/A000529/report")
        assert response.status_code == 200
        assert "case_report_text" in response.json()


def test_action_valid():
    with TestClient(app) as client:
        response = client.get("/api/accounts/A000529/action")
        assert response.status_code == 200
        assert response.json()["risk_tier"] in {
            "CRITICAL",
            "HIGH",
            "MEDIUM",
            "LOW",
        }


def test_audit():
    with TestClient(app) as client:
        response = client.get("/api/audit")
        assert response.status_code == 200
        assert "records" in response.json()


def test_metrics():
    with TestClient(app) as client:
        response = client.get("/api/metrics")
        assert response.status_code == 200
        assert "model_metrics" in response.json()


def test_failure_demo():
    with TestClient(app) as client:
        response = client.post("/api/failure-demo")
        assert response.status_code == 200
        assert response.json()["status"] == "GRACEFUL_FAILURE_HANDLED"


def test_address_normalize_unresolved():
    with TestClient(app) as client:
        response = client.post(
            "/api/address/normalize",
            json={"raw_address": "some random address"},
        )
        assert response.status_code == 200
        assert response.json()["requires_human_review"] is True


def test_timeline_valid():
    with TestClient(app) as client:
        response = client.get("/api/accounts/A000529/timeline")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert isinstance(data["events"], list)


def test_investigate_valid():
    with TestClient(app) as client:
        response = client.post("/api/accounts/A000529/investigate")
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "recommended_action" in data
        # Source can be either "llm" or "deterministic" depending on API key
        assert data["source"] in ["llm", "deterministic"]
