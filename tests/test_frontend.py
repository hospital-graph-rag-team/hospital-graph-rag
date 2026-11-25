import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

# Ensure src and root are in sys.path
ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
for p in [str(ROOT_DIR), str(SRC_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from frontend.components.graph_view import build_patient_knowledge_graph
from frontend.app import check_database_status


# =====================================================================
# 1. Knowledge Graph Construction & Deduplication Tests
# =====================================================================

def test_knowledge_graph_node_deduplication():
    """
    Verify that shared Doctor, Diagnosis, and Medication entities
    are deduplicated across multiple visits in the knowledge graph.
    """
    timeline = [
        {
            "visit_id": "V301",
            "visit_date": "2023-01-01",
            "admission_type": "Inpatient",
            "doctor_id": "DOC101",
            "doctor_name": "Dr. Strange",
            "specialty": "Cardiology",
            "diagnoses": [{"condition": "Hypertension", "diagnosis_id": "D001", "status": "Active"}],
            "prescriptions": [{"medication": "Lisinopril", "prescription_id": "RX001", "dosage": "10mg", "effective": True}],
            "lab_tests": [{"test_id": "T001", "test_name": "Systolic BP", "value": 150.0, "unit": "mmHg"}]
        },
        {
            "visit_id": "V302",
            "visit_date": "2023-02-01",
            "admission_type": "Follow-up",
            "doctor_id": "DOC101",  # Same doctor
            "doctor_name": "Dr. Strange",
            "specialty": "Cardiology",
            "diagnoses": [{"condition": "Hypertension", "diagnosis_id": "D002", "status": "Active"}],  # Same condition
            "prescriptions": [{"medication": "Lisinopril", "prescription_id": "RX002", "dosage": "10mg", "effective": True}],  # Same medication
            "lab_tests": [{"test_id": "T002", "test_name": "Systolic BP", "value": 135.0, "unit": "mmHg"}]  # Distinct test
        }
    ]
    profile = {"name": "Test Patient", "dob": "1980-01-01"}

    fig = build_patient_knowledge_graph("P101", timeline, profile)
    assert fig is not None

    # Inspect traces by name
    trace_names = [t.name for t in fig.data if t.name]
    assert any("Patient (1)" in name for name in trace_names)
    assert any("Visit (2)" in name for name in trace_names)
    assert any("Doctor (1)" in name for name in trace_names)  # Deduplicated to 1
    assert any("Diagnosis (1)" in name for name in trace_names)  # Deduplicated to 1
    assert any("Medication (1)" in name for name in trace_names)  # Deduplicated to 1
    assert any("LabTest (2)" in name for name in trace_names)  # 2 distinct tests


def test_knowledge_graph_empty_timeline():
    """Verify that an empty timeline renders gracefully without throwing exceptions."""
    fig = build_patient_knowledge_graph("P101", [], {"name": "Empty Patient"})
    assert fig is not None
    trace_names = [t.name for t in fig.data if t.name]
    assert any("Patient (1)" in name for name in trace_names)


# =====================================================================
# 2. Database Status Check Tests
# =====================================================================

def test_database_status_connected():
    """Verify check_database_status returns True when query succeeds."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.run.return_value.single.return_value = {"ping": 1}

    with patch("frontend.app.get_driver", return_value=mock_driver):
        assert check_database_status() is True


def test_database_status_disconnected():
    """Verify check_database_status returns False when exception occurs."""
    with patch("frontend.app.get_driver", side_effect=Exception("Connection refused")):
        assert check_database_status() is False


# =====================================================================
# 3. Streamlit AppTest Full Integration Tests
# =====================================================================

from streamlit.testing.v1 import AppTest

@pytest.fixture
def mock_backend_data():
    """Fixture providing complete mock responses for frontend rendering."""
    mock_patients = [
        {"patient_id": "P101", "name": "James Jones", "dob": "1971-12-21", "gender": "Male"},
        {"patient_id": "P102", "name": "Mary Smith", "dob": "1985-05-14", "gender": "Female"}
    ]
    mock_stats = {
        "totals": {
            "total_patients": 50,
            "total_doctors": 10,
            "total_visits": 146,
            "total_diagnosis_records": 146,
            "total_prescription_records": 146,
            "total_lab_records": 146,
            "total_nodes": 364,
            "total_relationships": 826
        },
        "conditions": [
            {"condition": "Hyperlipidemia", "patient_count": 20, "record_count": 54},
            {"condition": "Type 2 Diabetes", "patient_count": 15, "record_count": 45}
        ],
        "admission_types": [
            {"admission_type": "Follow-up", "count": 96},
            {"admission_type": "Outpatient", "count": 18}
        ]
    }
    mock_profile = {
        "patient_id": "P101",
        "name": "James Jones",
        "dob": "1971-12-21",
        "gender": "Male",
        "total_visits": 3,
        "first_visit_date": "2023-08-28",
        "latest_visit_date": "2023-10-18"
    }
    mock_timeline = [
        {
            "visit_id": "V301",
            "visit_date": "2023-08-28",
            "admission_type": "Inpatient",
            "doctor_id": "DOC207",
            "doctor_name": "Dr. Strange",
            "specialty": "Internal Medicine",
            "diagnoses": [{"condition": "Hyperlipidemia", "diagnosis_id": "D0001", "status": "Active"}],
            "prescriptions": [{"medication": "Rosuvastatin", "prescription_id": "RX0001", "dosage": "20mg", "effective": True}],
            "lab_tests": [{"test_id": "T0001", "test_name": "LDL Cholesterol", "value": 183.1, "unit": "mg/dL"}]
        }
    ]
    mock_trends = [
        {
            "test_name": "LDL Cholesterol",
            "unit": "mg/dL",
            "observation_count": 3,
            "initial_value": 183.1,
            "latest_value": 113.8,
            "absolute_change": -69.3,
            "percentage_change": -37.85,
            "direction": "decreased",
            "measurements": [
                {"date": "2023-08-28", "value": 183.1, "visit_id": "V301", "test_id": "T0001"},
                {"date": "2023-09-21", "value": 136.8, "visit_id": "V302", "test_id": "T0002"},
                {"date": "2023-10-18", "value": 113.8, "visit_id": "V303", "test_id": "T0003"}
            ]
        }
    ]
    mock_followup = [
        {
            "v1_id": "V301",
            "v2_id": "V302",
            "v1_date": "2023-08-28",
            "v2_date": "2023-09-21",
            "days_between": 24,
            "condition": "Hyperlipidemia",
            "medication_v2": "Rosuvastatin",
            "test_name": "LDL Cholesterol",
            "unit": "mg/dL",
            "v1_value": 183.1,
            "v2_value": 136.8,
            "absolute_delta": -46.3,
            "percentage_change": -25.29,
            "direction": "decreased"
        }
    ]
    mock_analytics = {
        "condition": "Type 2 Diabetes",
        "biomarker": "HbA1c",
        "unit": "%",
        "total_eligible_transitions": 30,
        "total_unique_patients": 15,
        "medications": [
            {
                "medication": "Glipizide",
                "biomarker": "HbA1c",
                "unit": "%",
                "unique_patient_count": 7,
                "eligible_transitions": 10,
                "improved_transitions": 7,
                "worsened_transitions": 3,
                "unchanged_transitions": 0,
                "betterment_rate_pct": 70.0,
                "evidence_sample": []
            }
        ],
        "disclaimer": "Synthetic observational outcomes."
    }

    return {
        "patients": mock_patients,
        "stats": mock_stats,
        "profile": mock_profile,
        "timeline": mock_timeline,
        "trends": mock_trends,
        "followup": mock_followup,
        "analytics": mock_analytics
    }


@pytest.fixture(autouse=True)
def mock_default_overview_stats(mock_backend_data):
    """Ensure AppTest never attempts external network calls on initial startup."""
    mock_db_driver = MagicMock()
    mock_session = MagicMock()
    mock_db_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.run.return_value.single.return_value = {"ping": 1}

    with patch("frontend.components.dashboard.get_hospital_overview_stats", return_value=mock_backend_data["stats"]), \
         patch("src.graph.retrieval.get_hospital_overview_stats", return_value=mock_backend_data["stats"]), \
         patch("frontend.app.get_patient_directory", return_value=mock_backend_data["patients"]), \
         patch("src.graph.retrieval.get_patient_directory", return_value=mock_backend_data["patients"]), \
         patch("src.graph.connection.get_driver", return_value=mock_db_driver), \
         patch("frontend.app.get_driver", return_value=mock_db_driver), \
         patch("frontend.app.check_database_status", return_value=True):
        yield


def test_apptest_startup_hospital_overview(mock_backend_data):
    """Test initial app launch on Hospital Overview tab without errors."""
    at = AppTest.from_file(str(ROOT_DIR / "frontend" / "app.py"))
    at.run(timeout=10)

    assert not at.exception
    # Verify title and academic disclaimer
    assert any("Academic demonstration" in banner.value for banner in at.markdown)
    assert any("Hospital Overview" in sub.value for sub in at.subheader)


def test_apptest_navigation_patient_explorer(mock_backend_data):
    """Test navigating to Patient Explorer and selecting a patient."""
    with patch("frontend.components.patient_view.get_patient_profile", return_value=mock_backend_data["profile"]), \
         patch("src.graph.retrieval.get_patient_profile", return_value=mock_backend_data["profile"]), \
         patch("frontend.components.patient_view.get_patient_timeline", return_value=mock_backend_data["timeline"]), \
         patch("src.graph.retrieval.get_patient_timeline", return_value=mock_backend_data["timeline"]), \
         patch("frontend.components.patient_view.get_lab_trends", return_value=mock_backend_data["trends"]), \
         patch("src.graph.retrieval.get_lab_trends", return_value=mock_backend_data["trends"]), \
         patch("frontend.components.patient_view.get_followup_comparison", return_value=mock_backend_data["followup"]), \
         patch("src.graph.retrieval.get_followup_comparison", return_value=mock_backend_data["followup"]):

        at = AppTest.from_file(str(ROOT_DIR / "frontend" / "app.py"))
        at.run(timeout=10)
        assert not at.exception

        # Switch radio to Patient Explorer
        at.sidebar.radio[0].set_value("Patient Explorer")
        # Select patient P101
        at.sidebar.selectbox[0].set_value("P101 — James Jones")
        at.run(timeout=10)

        assert not at.exception
        assert any("Patient Explorer" in sub.value for sub in at.subheader)
        # Check that James Jones profile rendered
        assert any("James Jones" in m.value for m in at.markdown)


def test_apptest_navigation_medication_analytics(mock_backend_data):
    """Test navigating to Medication Analytics view and rendering condition metrics."""
    with patch("frontend.components.analytics.get_medication_outcomes", return_value=mock_backend_data["analytics"]), \
         patch("src.graph.retrieval.get_medication_outcomes", return_value=mock_backend_data["analytics"]):

        at = AppTest.from_file(str(ROOT_DIR / "frontend" / "app.py"))
        at.run(timeout=10)
        assert not at.exception

        # Switch radio to Medication Analytics
        at.sidebar.radio[0].set_value("Medication Analytics")
        at.run(timeout=10)

        assert not at.exception
        assert any("Medication Analytics" in sub.value for sub in at.subheader)
        assert any("Observational Association Disclaimer" in m.value for m in at.markdown)


def test_apptest_navigation_knowledge_graph(mock_backend_data):
    """Test navigating to Patient Knowledge Graph view with active patient."""
    with patch("frontend.components.graph_view.get_patient_timeline", return_value=mock_backend_data["timeline"]), \
         patch("src.graph.retrieval.get_patient_timeline", return_value=mock_backend_data["timeline"]), \
         patch("frontend.components.graph_view.get_patient_profile", return_value=mock_backend_data["profile"]), \
         patch("src.graph.retrieval.get_patient_profile", return_value=mock_backend_data["profile"]):

        at = AppTest.from_file(str(ROOT_DIR / "frontend" / "app.py"))
        at.run(timeout=10)
        assert not at.exception

        # Select patient P101 and switch to Knowledge Graph
        at.sidebar.selectbox[0].set_value("P101 — James Jones")
        at.sidebar.radio[0].set_value("Patient Knowledge Graph")
        at.run(timeout=10)

        assert not at.exception
        assert any("Patient Knowledge Graph Visualization" in sub.value for sub in at.subheader)


def test_apptest_chat_patient_context_switching_isolation(mock_backend_data):
    """
    Verify that switching patient context clears conversation history
    to prevent cross-patient context contamination.
    """
    at = AppTest.from_file(str(ROOT_DIR / "frontend" / "app.py"))
    at.run(timeout=10)
    assert not at.exception

    # Switch to AI Assistant with P101
    at.sidebar.selectbox[0].set_value("P101 — James Jones")
    at.sidebar.radio[0].set_value("AI Assistant")
    at.run(timeout=10)

    # Inject a message into session state for P101
    at.session_state["messages"] = [
        {"role": "user", "content": "What is P101's diagnosis?"},
        {"role": "assistant", "answer": "P101 has Hyperlipidemia.", "citations": ["P101"]}
    ]
    at.session_state["chat_patient_id"] = "P101"

    # Switch patient in sidebar to second patient (options[2])
    second_patient_opt = at.sidebar.selectbox[0].options[2]
    second_pid = second_patient_opt.split(" — ")[0].strip()
    at.sidebar.selectbox[0].set_value(second_patient_opt)
    at.run(timeout=10)

    assert not at.exception
    # Chat patient context mismatch must trigger conversation reset
    assert at.session_state["messages"] == []
    assert at.session_state["chat_patient_id"] == second_pid
