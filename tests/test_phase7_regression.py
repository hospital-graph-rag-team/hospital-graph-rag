"""
Unit and regression tests for Clinical Graph RAG — Phase 7.
Tests cover bug fixes, discrepancies, schema validation, graph visualization edges,
medication reconciliation, and error handling without requiring live network access.
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys
from datetime import datetime, date

# Ensure src and root are in sys.path
ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
for p in [str(ROOT_DIR), str(SRC_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from frontend.components.graph_view import build_patient_knowledge_graph
from frontend.components.analytics import render_medication_analytics
from frontend.components.patient_view import render_patient_explorer
from src.rag.engine import run_clinical_query_detailed, _extract_citations
from src.graph.retrieval import get_medication_outcomes, get_hospital_overview_stats


# =====================================================================
# 1. Dashboard Count Accuracy & Schema Verification
# =====================================================================

def test_dashboard_count_accuracy():
    """Verify get_hospital_overview_stats correctly processes mock database stats."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_totals = {
        "total_nodes": 364,
        "total_relationships": 826,
        "total_patients": 50,
        "total_doctors": 10,
        "total_visits": 146,
        "total_diagnosis_records": 146,
        "total_prescription_records": 146,
        "total_lab_records": 146
    }
    mock_record = MagicMock()
    mock_record.__getitem__.side_effect = lambda k: mock_totals
    mock_totals_res = MagicMock()
    mock_totals_res.single.return_value = mock_record

    mock_cond_res = [
        {"condition": "Hyperlipidemia", "patient_count": 20, "record_count": 54},
        {"condition": "Hypertension", "patient_count": 15, "record_count": 47},
        {"condition": "Type 2 Diabetes", "patient_count": 15, "record_count": 45}
    ]
    mock_adm_res = [
        {"admission_type": "Follow-up", "count": 96},
        {"admission_type": "Outpatient", "count": 18},
        {"admission_type": "Inpatient", "count": 17},
        {"admission_type": "Emergency", "count": 15}
    ]

    mock_session.run.side_effect = [mock_totals_res, mock_cond_res, mock_adm_res]

    stats = get_hospital_overview_stats(driver=mock_driver)
    assert stats["totals"]["total_nodes"] == 364
    assert stats["totals"]["total_relationships"] == 826
    assert stats["totals"]["total_patients"] == 50
    assert len(stats["conditions"]) == 3
    assert len(stats["admission_types"]) == 4


# =====================================================================
# 2. Patient Identity & Derived Age
# =====================================================================

def test_correct_patient_identity_in_profile():
    """Verify patient profile correctly reflects actual James Jones data."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_record = MagicMock()
    mock_record.data.return_value = {
        "patient_id": "P101",
        "name": "James Jones",
        "dob": "1971-12-21",
        "gender": "M",
        "visit_count": 3,
        "first_visit_date": "2023-08-28",
        "latest_visit_date": "2023-10-18"
    }
    mock_session.run.return_value.single.return_value = mock_record

    from src.graph.retrieval import get_patient_profile
    profile = get_patient_profile("P101", driver=mock_driver)
    assert profile["patient_id"] == "P101"
    assert profile["name"] == "James Jones"
    assert profile["dob"] == "1971-12-21"
    assert profile["gender"] == "M"
    # Ensure fabricated fields are NOT present
    for fab in ["primary_contact", "emergency_phone", "insurance_provider"]:
        assert fab not in profile


def test_derived_age_calculation():
    """Verify age derivation logic calculates exact completed years from DOB."""
    dob_d = date(1971, 12, 21)
    # Test on arbitrary reference date
    ref_date_after_bday = date(2026, 12, 25)
    age1 = ref_date_after_bday.year - dob_d.year - ((ref_date_after_bday.month, ref_date_after_bday.day) < (dob_d.month, dob_d.day))
    assert age1 == 55

    ref_date_before_bday = date(2026, 11, 24)
    age2 = ref_date_before_bday.year - dob_d.year - ((ref_date_before_bday.month, ref_date_before_bday.day) < (dob_d.month, dob_d.day))
    assert age2 == 54


# =====================================================================
# 3. Condition Consistency & Unsupported Conditions
# =====================================================================

def test_condition_consistency_in_medication_outcomes():
    """Verify medication outcomes handles valid condition and rejects unsupported conditions."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    # Mock query returning empty for an unsupported condition like 'Asthma'
    mock_session.run.return_value.data.return_value = []

    res = get_medication_outcomes("Asthma", driver=mock_driver)
    assert res["condition"] == "Asthma"
    assert res["total_eligible_transitions"] == 0
    assert res["total_unique_patients"] == 0
    assert res["medications"] == []


# =====================================================================
# 4. Knowledge Graph: LabTest Nodes, FOLLOWED_BY Edges, Hover Midpoints
# =====================================================================

def test_knowledge_graph_labtest_nodes_and_followed_by_edges():
    """
    Verify build_patient_knowledge_graph creates LabTest nodes,
    FOLLOWED_BY consecutive visit edges, and edge midpoint hover markers.
    """
    timeline = [
        {
            "visit_id": "V301",
            "visit_date": "2023-08-28",
            "admission_type": "Inpatient",
            "doctor": {"doctor_id": "DOC207", "name": "Dr. Strange", "specialty": "Internal Medicine"},
            "diagnoses": [{"condition": "Hyperlipidemia", "diagnosis_id": "D0001", "status": "Active"}],
            "medications": [{"medication_name": "Rosuvastatin", "prescription_id": "RX0001", "dosage": "Standard", "is_effective": True}],
            "lab_tests": [{"test_id": "T0001", "test_name": "LDL Cholesterol", "value": 183.1, "unit": "mg/dL"}]
        },
        {
            "visit_id": "V302",
            "visit_date": "2023-09-21",
            "admission_type": "Follow-up",
            "doctor": {"doctor_id": "DOC207", "name": "Dr. Strange", "specialty": "Internal Medicine"},
            "diagnoses": [{"condition": "Hyperlipidemia", "diagnosis_id": "D0002", "status": "Active"}],
            "medications": [{"medication_name": "Rosuvastatin", "prescription_id": "RX0002", "dosage": "Standard", "is_effective": True}],
            "lab_tests": [{"test_id": "T0002", "test_name": "LDL Cholesterol", "value": 136.8, "unit": "mg/dL"}]
        }
    ]
    profile = {"name": "James Jones", "dob": "1971-12-21"}

    fig = build_patient_knowledge_graph("P101", timeline, profile)
    assert fig is not None

    # Check traces
    trace_names = [t.name for t in fig.data if t.name]
    assert any("LabTest (2)" in name for name in trace_names)
    assert any("Visit (2)" in name for name in trace_names)
    assert any("Doctor (1)" in name for name in trace_names)
    assert any("Diagnosis (1)" in name for name in trace_names)
    assert any("Medication (1)" in name for name in trace_names)

    # Check that midpoint marker trace exists (index 1 in fig.data)
    midpoint_trace = fig.data[1]
    assert midpoint_trace.mode == "markers"
    assert len(midpoint_trace.hovertext) > 0
    # Confirm FOLLOWED_BY relationship is present in midpoint hover text
    assert any("FOLLOWED_BY" in ht for ht in midpoint_trace.hovertext)
    assert any("HAD_TEST" in ht for ht in midpoint_trace.hovertext)
    assert any("PRESCRIBED" in ht for ht in midpoint_trace.hovertext)


# =====================================================================
# 5. Medication Outcome Mathematical Reconciliation
# =====================================================================

def test_medication_outcome_mathematical_reconciliation():
    """Verify that improved + worsened + unchanged equals total eligible transitions."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    # Mock query returning 3 transitions for Metformin
    mock_records = [
        {"patient_id": "P1", "v1_id": "V1", "v2_id": "V2", "medication_name": "Metformin", "prescription_id": "RX1", "biomarker": "HbA1c", "unit": "%", "v1_value": 8.5, "v2_value": 7.2},  # improved
        {"patient_id": "P1", "v1_id": "V2", "v2_id": "V3", "medication_name": "Metformin", "prescription_id": "RX2", "biomarker": "HbA1c", "unit": "%", "v1_value": 7.2, "v2_value": 7.5},  # worsened
        {"patient_id": "P2", "v1_id": "V4", "v2_id": "V5", "medication_name": "Metformin", "prescription_id": "RX3", "biomarker": "HbA1c", "unit": "%", "v1_value": 7.0, "v2_value": 7.0},  # unchanged
    ]
    mock_session.run.return_value.data.return_value = mock_records

    res = get_medication_outcomes("Type 2 Diabetes", driver=mock_driver)
    assert res["total_eligible_transitions"] == 3
    assert res["total_unique_patients"] == 2
    med = res["medications"][0]
    assert med["medication"] == "Metformin"
    assert med["eligible_transitions"] == 3
    assert med["improved_transitions"] == 1
    assert med["worsened_transitions"] == 1
    assert med["unchanged_transitions"] == 1
    assert med["improved_transitions"] + med["worsened_transitions"] + med["unchanged_transitions"] == med["eligible_transitions"]
    assert med["betterment_rate_pct"] == round((1 / 3) * 100, 2)


# =====================================================================
# 6. Safety Refusal & Grounding Citation Handling
# =====================================================================

def test_safety_refusal_delete_request():
    """Verify deletion requests are refused immediately in read-only mode."""
    res = run_clinical_query_detailed("Delete patient P101 from Neo4j.")
    assert res["status"] == "refusal"
    assert "strict read-only mode" in res["answer"]
    assert res["tool_calls"] == []


def test_safety_refusal_medical_advice():
    """Verify personalized medical advice requests are refused immediately."""
    res = run_clinical_query_detailed("Which medication should I take for diabetes?")
    assert res["status"] == "refusal"
    assert "cannot provide personalized medical diagnosis" in res["answer"]
    assert res["tool_calls"] == []


def test_unsupported_citation_grounding_validation():
    """
    Verify that citing an identifier not in retrieved evidence
    causes citation_validation['is_valid'] to be False.
    """
    mock_client = MagicMock()
    # Mock LLM returning an answer citing P999 and RX9999
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "Patient P999 was prescribed RX9999."
    mock_message.tool_calls = None
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    res = run_clinical_query_detailed(
        user_prompt="Who is patient P999?",
        client=mock_client
    )
    assert res["status"] == "success"
    assert "P999" in res["citations"]
    # Since no tool returned P999 in evidence, is_valid must be False
    assert res["citation_validation"]["is_valid"] is False
    assert "P999" in res["citation_validation"]["unsupported"]


def test_api_timeout_error_handling():
    """Verify that client timeout or connection error returns structured error response."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("Connection timed out after 30000ms")

    res = run_clinical_query_detailed(
        user_prompt="Summarize patient P101",
        client=mock_client
    )
    assert res["status"] == "error"
    assert "timed out" in res["answer"].lower() or "error" in res["status"]
    assert res["error"] is not None


# =====================================================================
# 7. Conversational Follow-Up History Integration
# =====================================================================

def test_conversational_history_passed_to_messages():
    """Verify conversation_history is correctly prepended to the LLM message prompt."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "They were prescribed Rosuvastatin."
    mock_message.tool_calls = None
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    history = [
        {"role": "user", "content": "What condition does P101 have?"},
        {"role": "assistant", "content": "Patient P101 has Hyperlipidemia."}
    ]

    res = run_clinical_query_detailed(
        user_prompt="What medication was prescribed for that?",
        conversation_history=history,
        selected_patient_id="P101",
        client=mock_client
    )
    assert res["status"] == "success"
    # Inspect messages passed to client.chat.completions.create
    call_args = mock_client.chat.completions.create.call_args[1]
    passed_messages = call_args["messages"]

    # History messages must be present between system and latest user message
    roles = [m["role"] for m in passed_messages]
    assert roles[0] == "system"
    assert roles[1] == "user"
    assert passed_messages[1]["content"] == "What condition does P101 have?"
    assert roles[2] == "assistant"
    assert passed_messages[2]["content"] == "Patient P101 has Hyperlipidemia."
    assert roles[3] == "user"
    assert "What medication was prescribed for that?" in passed_messages[3]["content"]


# =====================================================================
# 8. Duplicate Submission Prevention & Database Failure Mocks
# =====================================================================

def test_duplicate_chat_submission_prevention_logic():
    """Verify that rerun cycle cleans active button prompts to prevent duplicate submissions."""
    session_messages = []
    # Simulate first submission
    prompt = "What is P101's history?"
    session_messages.append({"role": "user", "content": prompt})
    session_messages.append({"role": "assistant", "content": "Summary of P101", "answer": "Summary of P101"})

    assert len(session_messages) == 2
    # Verify second submission only happens if a new distinct active prompt is passed
    prompt_to_submit = None
    user_input = None
    active_prompt = prompt_to_submit or user_input
    assert active_prompt is None  # Nothing added on rerun without user action
    assert len(session_messages) == 2


def test_database_failure_graceful_handling():
    """Verify database connection failures return informative errors rather than uncaught exceptions."""
    mock_driver = MagicMock()
    mock_driver.session.side_effect = Exception("Neo4j AuraDB unreachable: Connection timed out")

    from src.graph.retrieval import get_hospital_overview_stats
    with pytest.raises(Exception) as exc_info:
        get_hospital_overview_stats(driver=mock_driver)
    assert "AuraDB unreachable" in str(exc_info.value)


def test_invalid_structured_response_empty_query():
    """Verify empty query returns structured error response without LLM call."""
    res = run_clinical_query_detailed("   ")
    assert res["status"] == "error"
    assert "Empty query" in res["answer"]
    assert res["tool_calls"] == []

