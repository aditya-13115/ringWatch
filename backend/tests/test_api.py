from fastapi.testclient import TestClient

from backend.main import app


def get_first_account_id(client):
    response = client.get("/api/queue")
    assert response.status_code == 200
    data = response.json()
    assert len(data["accounts"]) > 0
    return data["accounts"][0]["account_id"]


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
        assert data["total"] > 0
        assert 0 < len(data["accounts"]) <= data["total"]


def test_account_detail_valid():
    with TestClient(app) as client:
        account_id = get_first_account_id(client)
        response = client.get(f"/api/accounts/{account_id}")
        assert response.status_code == 200
        assert response.json()["account_id"] == account_id


def test_account_detail_not_found():
    with TestClient(app) as client:
        response = client.get("/api/accounts/UNKNOWN")
        assert response.status_code == 404


def test_graph_valid():
    with TestClient(app) as client:
        account_id = get_first_account_id(client)
        response = client.get(f"/api/accounts/{account_id}/graph")
        assert response.status_code == 200
        assert "nodes" in response.json()
        assert "edges" in response.json()


def test_evidence_valid():
    with TestClient(app) as client:
        account_id = get_first_account_id(client)
        response = client.get(f"/api/accounts/{account_id}/evidence")
        assert response.status_code == 200
        assert "fields" in response.json()


def test_report_valid():
    with TestClient(app) as client:
        account_id = get_first_account_id(client)
        response = client.get(f"/api/accounts/{account_id}/report")
        assert response.status_code == 200
        assert "case_report_text" in response.json()


def test_action_valid():
    with TestClient(app) as client:
        account_id = get_first_account_id(client)
        response = client.get(f"/api/accounts/{account_id}/action")
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
        account_id = get_first_account_id(client)
        response = client.get(f"/api/accounts/{account_id}/timeline")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert isinstance(data["events"], list)


def test_investigate_valid():
    with TestClient(app) as client:
        account_id = get_first_account_id(client)
        response = client.post(f"/api/accounts/{account_id}/investigate")
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "recommended_action" in data
        assert data["source"] in ["llm", "deterministic"]


def test_failure_demo_razorpay():
    with TestClient(app) as client:
        response = client.post("/api/failure-demo/razorpay-synthetic")

        assert response.status_code == 200

        data = response.json()

        assert data["status"] == "GRACEFUL_FAILURE_HANDLED"
        assert data["source"] == "razorpay_style_synthetic"

        assert data["batch_size"] == 100
        assert data["malformed_rows"] == 10
        assert data["quarantined"] == 10
        assert data["valid_processed"] == 90
        assert data["human_review_routed"] == 10

        assert data["safety"]["malformed_entered_investigation_pipeline"] is False

        assert data["safety"]["quarantined_before_model_inference"] is True

        assert data["safety"]["human_review_required"] is True


def test_feature_ablation_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/metrics/feature-ablation")
        assert response.status_code == 200
        data = response.json()
        assert data["model_version"] == "LightGBM_Model_A_Tuned"
        assert data["test_accounts"] > 0
        assert len(data["features"]) > 0


def test_graph_overview_includes_community_and_strongest_relationship():
    with TestClient(app) as client:
        queue = client.get("/api/queue?limit=1").json()
        account_id = queue["accounts"][0]["account_id"]
        response = client.get(f"/api/accounts/{account_id}")
        assert response.status_code == 200
        evidence = response.json()["graph_evidence"]
        assert "community_id" in evidence
        assert "strongest_edge_explanation" in evidence
        assert evidence["strongest_edge_explanation"]


def test_audit_exposes_auditability_fields():
    with TestClient(app) as client:
        response = client.get("/api/audit")
        assert response.status_code == 200
        records = response.json()["records"]
        assert records
        record = records[0]
        assert record["input_data_hash"]
        assert record["threshold_used"] is not None
        assert "human_decision" in record
        assert "outcome" in record
        assert "error_path" in record
