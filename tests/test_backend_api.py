"""Automated tests for the ClinicalGraph 2.0 FastAPI backend."""

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pytest

from backend.main import create_app
from backend.security import api_rate_limiter, chat_rate_limiter
from backend.services.graph_service import build_patient_subgraph, get_neo4j_driver


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    api_rate_limiter.reset()
    chat_rate_limiter.reset()
    yield
    api_rate_limiter.reset()
    chat_rate_limiter.reset()


@pytest.fixture
def mock_driver():
    return MagicMock()


@pytest.fixture
def client(mock_driver, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.delenv("BACKEND_API_TOKEN", raising=False)
    monkeypatch.setenv("NEO4J_URI", "neo4j+s://mock.databases.neo4j.io")
    monkeypatch.setenv("NEO4J_PASSWORD", "mock_secret_pw")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_mock_key_value")

    app = create_app()
    app.dependency_overrides[get_neo4j_driver] = lambda: mock_driver
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


def test_health_endpoint_ok(client):
    with patch("backend.routers.health.check_neo4j_connectivity", return_value=True):
        res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["neo4j_connected"] is True
    assert body["groq_configured"] is True
    assert "mock_secret_pw" not in res.text
    assert "gsk_mock_key_value" not in res.text


def test_health_endpoint_degraded_when_neo4j_down(client):
    with patch("backend.routers.health.check_neo4j_connectivity", return_value=False):
        res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "degraded"
    assert body["neo4j_connected"] is False


def test_backend_token_authentication_enforced(mock_driver, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("BACKEND_API_TOKEN", "super-secret-token-123")
    app = create_app()
    app.dependency_overrides[get_neo4j_driver] = lambda: mock_driver

    with TestClient(app) as tc:
        unauth = tc.get("/api/v1/patients")
        assert unauth.status_code == 401

        wrong = tc.get("/api/v1/patients", headers={"X-Backend-Token": "wrong"})
        assert wrong.status_code == 401

        with patch(
            "backend.routers.patients.get_patients_directory_enriched",
            return_value=[],
        ):
            ok = tc.get(
                "/api/v1/patients",
                headers={"X-Backend-Token": "super-secret-token-123"},
            )
            assert ok.status_code == 200
            bearer_ok = tc.get(
                "/api/v1/patients",
                headers={"Authorization": "Bearer super-secret-token-123"},
            )
            assert bearer_ok.status_code == 200
    app.dependency_overrides.clear()


def test_production_fails_closed_without_token(mock_driver, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("BACKEND_API_TOKEN", raising=False)
    app = create_app()
    app.dependency_overrides[get_neo4j_driver] = lambda: mock_driver

    with TestClient(app) as tc:
        res = tc.get("/api/v1/patients")
        assert res.status_code == 503
    app.dependency_overrides.clear()


def test_patient_id_validation_rejects_malformed_ids(client):
    res = client.get("/api/v1/patients/INVALID_ID!")
    assert res.status_code == 422


def test_missing_patient_returns_404(client):
    with patch("backend.routers.patients.get_patient_profile_enriched", return_value=None):
        res = client.get("/api/v1/patients/P9999")
    assert res.status_code == 404

    with patch("backend.routers.patients.get_patient_profile", return_value=None):
        res_tl = client.get("/api/v1/patients/P9999/timeline")
        assert res_tl.status_code == 404


def test_overview_endpoint_and_neo4j_error_sanitization(client):
    sample = {
        "time_range": "all",
        "totals": {
            "total_nodes": 364,
            "total_relationships": 826,
            "total_patients": 50,
            "total_doctors": 10,
            "total_visits": 146,
            "total_diagnosis_records": 146,
            "total_prescription_records": 146,
            "total_lab_records": 146,
            "total_clinical_records": 438,
        },
        "conditions": [{"condition": "Hyperlipidemia", "patient_count": 20, "record_count": 54}],
        "admission_types": [{"admission_type": "Follow-up", "count": 96}],
        "visits_over_time": [{"month": "2024-08", "total_visits": 8, "follow_up": 6, "outpatient": 1, "inpatient": 1, "emergency": 0}],
        "recent_encounters": [],
        "schema_nodes": [{"label": "Patient", "count": 50}],
        "schema_relationships": [{"relationship_type": "HAD_VISIT", "count": 146}],
    }
    with patch("backend.routers.overview.get_overview_data", return_value=sample):
        res = client.get("/api/v1/overview?time_range=6m")
    assert res.status_code == 200
    assert res.json()["totals"]["total_patients"] == 50

    with patch(
        "backend.routers.overview.get_overview_data",
        side_effect=RuntimeError("Failed connecting to neo4j+ssc://secret.databases.neo4j.io with password=xyz"),
    ):
        err_res = client.get("/api/v1/overview")
    assert err_res.status_code == 503
    assert "secret.databases.neo4j.io" not in err_res.text
    assert "password=xyz" not in err_res.text
    assert "[REDACTED]" in err_res.text


def test_patient_graph_deduplication_preserves_shared_entities():
    profile = {"patient_id": "P101", "name": "James Jones", "dob": "1971-12-21", "gender": "M", "visit_count": 2}
    timeline = [
        {
            "visit_id": "V301",
            "visit_date": "2023-08-28",
            "admission_type": "Inpatient",
            "doctor": {"doctor_id": "DOC207", "name": "Dr. Stephen Strange", "specialty": "Cardiology"},
            "diagnoses": [{"diagnosis_id": "D0001", "condition": "Hyperlipidemia", "status": "Active"}],
            "medications": [{"prescription_id": "RX0001", "medication_name": "Rosuvastatin", "dosage": "Standard", "is_effective": True}],
            "lab_tests": [{"test_id": "T0001", "test_name": "LDL Cholesterol", "value": 183.1, "unit": "mg/dL"}],
        },
        {
            "visit_id": "V302",
            "visit_date": "2023-09-21",
            "admission_type": "Follow-up",
            "doctor": {"doctor_id": "DOC207", "name": "Dr. Stephen Strange", "specialty": "Cardiology"},
            "diagnoses": [{"diagnosis_id": "D0002", "condition": "Hyperlipidemia", "status": "Active"}],
            "medications": [{"prescription_id": "RX0002", "medication_name": "Rosuvastatin", "dosage": "Standard", "is_effective": True}],
            "lab_tests": [{"test_id": "T0002", "test_name": "LDL Cholesterol", "value": 136.8, "unit": "mg/dL"}],
        },
    ]

    graph = build_patient_subgraph("P101", profile, timeline)
    assert graph.stats.node_counts_by_type["Patient"] == 1
    assert graph.stats.node_counts_by_type["Visit"] == 2
    assert graph.stats.node_counts_by_type["Doctor"] == 1
    assert graph.stats.node_counts_by_type["Diagnosis"] == 1
    assert graph.stats.node_counts_by_type["Medication"] == 1
    assert graph.stats.node_counts_by_type["LabTest"] == 2
    assert graph.stats.edge_counts_by_type["FOLLOWED_BY"] == 1


def test_medication_analytics_endpoint(client):
    mock_payload = {
        "condition": "Type 2 Diabetes",
        "biomarker": "HbA1c",
        "unit": "%",
        "total_eligible_transitions": 30,
        "total_unique_patients": 15,
        "medications": [
            {
                "medication": "Metformin",
                "biomarker": "HbA1c",
                "unit": "%",
                "unique_patient_count": 6,
                "eligible_transitions": 12,
                "improved_transitions": 10,
                "worsened_transitions": 2,
                "unchanged_transitions": 0,
                "betterment_rate_pct": 83.33,
                "evidence_sample": [],
            }
        ],
        "disclaimer": "Synthetic observational outcomes.",
    }
    with patch("backend.routers.analytics.get_medication_outcomes", return_value=mock_payload):
        res = client.get("/api/v1/analytics/medications?condition=Type%202%20Diabetes")
    assert res.status_code == 200
    assert res.json()["medications"][0]["medication"] == "Metformin"


def test_chat_endpoint_success_validation_and_rate_limit(client, monkeypatch):
    # 1. Empty query rejected
    empty_res = client.post("/api/v1/chat", json={"query": ""})
    assert empty_res.status_code == 422

    # 2. Invalid patient context rejected
    bad_ctx = client.post(
        "/api/v1/chat",
        json={"query": "Show history", "selected_patient_id": "DROP TABLE"},
    )
    assert bad_ctx.status_code == 422

    # 3. Normal RAG execution mocked cleanly
    mock_rag = {
        "query": "Summarize P101",
        "patient_id": "P101",
        "status": "success",
        "answer": "Patient P101 had visit V301.",
        "citations": ["P101", "V301"],
        "citation_validation": {"supported": ["P101", "V301"], "unsupported": [], "is_valid": True},
        "tool_calls": [{"tool": "get_patient_timeline", "arguments": {"patient_id": "P101"}, "summary": "Retrieved 3 visits"}],
        "retrieved_evidence": [{"tool": "get_patient_timeline", "data": []}],
        "error": None,
    }
    with patch("backend.services.chat_service.run_clinical_query_detailed", return_value=mock_rag):
        ok_res = client.post(
            "/api/v1/chat",
            json={"query": "Summarize P101", "selected_patient_id": "P101"},
        )
    assert ok_res.status_code == 200
    assert ok_res.json()["citations"] == ["P101", "V301"]

    # 4. Groq failure sanitized (does not leak gsk_ key)
    with patch(
        "backend.services.chat_service.run_clinical_query_detailed",
        side_effect=RuntimeError("Groq failed with key gsk_12345secret"),
    ):
        fail_res = client.post("/api/v1/chat", json={"query": "Summarize P101"})
    assert fail_res.status_code == 200
    assert fail_res.json()["status"] == "error"
    assert "gsk_12345secret" not in fail_res.text

    # 5. Rate limiting triggers 429
    monkeypatch.setenv("CHAT_RATE_LIMIT_PER_MINUTE", "2")
    chat_rate_limiter.reset()
    with patch("backend.services.chat_service.run_clinical_query_detailed", return_value=mock_rag):
        r1 = client.post("/api/v1/chat", json={"query": "Q1"})
        r2 = client.post("/api/v1/chat", json={"query": "Q2"})
        r3 = client.post("/api/v1/chat", json={"query": "Q3"})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
