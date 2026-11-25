import pytest
from pathlib import Path
import sys
from unittest.mock import MagicMock
import pandas as pd

# Add src to Python path
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph.verify_graph import (
    derive_expected_metrics,
    verify_node_counts,
    verify_relationship_counts,
    verify_trajectories,
    verify_constraints,
    verify_live_graph,
)


@pytest.fixture
def synthetic_graph_csv_dir(tmp_path):
    """Generates synthetic CSV files for offline verification testing."""
    patients = pd.DataFrame([
        {"patient_id": "P101", "name": "John Doe", "dob": "1980-01-01", "gender": "M"},
        {"patient_id": "P102", "name": "Jane Smith", "dob": "1990-05-15", "gender": "F"},
    ])
    doctors = pd.DataFrame([
        {"doctor_id": "DOC201", "name": "Dr. Gregory House", "specialty": "Internal Medicine"},
    ])
    visits = pd.DataFrame([
        {"visit_id": "V301", "patient_id": "P101", "doctor_id": "DOC201", "visit_date": "2023-01-10", "admission_type": "Inpatient"},
        {"visit_id": "V302", "patient_id": "P101", "doctor_id": "DOC201", "visit_date": "2023-02-15", "admission_type": "Follow-up"},
        {"visit_id": "V303", "patient_id": "P102", "doctor_id": "DOC201", "visit_date": "2023-03-01", "admission_type": "Outpatient"},
    ])
    diagnoses = pd.DataFrame([
        {"diagnosis_id": "D0001", "visit_id": "V301", "condition": "Type 2 Diabetes", "status": "Active"},
        {"diagnosis_id": "D0002", "visit_id": "V302", "condition": "Type 2 Diabetes", "status": "Active"},
        {"diagnosis_id": "D0003", "visit_id": "V303", "condition": "Hypertension", "status": "Active"},
    ])
    medications = pd.DataFrame([
        {"prescription_id": "RX0001", "visit_id": "V301", "medication_name": "Metformin", "dosage": "Standard", "is_effective": True},
        {"prescription_id": "RX0002", "visit_id": "V302", "medication_name": "Metformin", "dosage": "Standard", "is_effective": True},
        {"prescription_id": "RX0003", "visit_id": "V303", "medication_name": "Amlodipine", "dosage": "Standard", "is_effective": False},
    ])
    lab_tests = pd.DataFrame([
        {"test_id": "T0001", "visit_id": "V301", "test_name": "HbA1c", "value": 8.5, "unit": "%"},
        {"test_id": "T0002", "visit_id": "V302", "test_name": "HbA1c", "value": 6.8, "unit": "%"},
        {"test_id": "T0003", "visit_id": "V303", "test_name": "Systolic BP", "value": 150.0, "unit": "mmHg"},
    ])

    patients.to_csv(tmp_path / "patients.csv", index=False)
    doctors.to_csv(tmp_path / "doctors.csv", index=False)
    visits.to_csv(tmp_path / "visits.csv", index=False)
    diagnoses.to_csv(tmp_path / "diagnoses.csv", index=False)
    medications.to_csv(tmp_path / "medications.csv", index=False)
    lab_tests.to_csv(tmp_path / "lab_tests.csv", index=False)

    return tmp_path


def test_derive_expected_metrics(synthetic_graph_csv_dir):
    """Verifies that expected graph metrics are dynamically computed from CSVs."""
    metrics = derive_expected_metrics(synthetic_graph_csv_dir)

    # Node count expectations (deduplicating Diagnosis and Medication)
    assert metrics["nodes"]["Patient"] == 2
    assert metrics["nodes"]["Doctor"] == 1
    assert metrics["nodes"]["Visit"] == 3
    assert metrics["nodes"]["Diagnosis"] == 2  # Type 2 Diabetes, Hypertension
    assert metrics["nodes"]["Medication"] == 2  # Metformin, Amlodipine
    assert metrics["nodes"]["LabTest"] == 3

    # Dynamic FOLLOWED_BY count: P101 has 2 visits (1 transition: V301->V302); P102 has 1 visit (0 transitions)
    assert metrics["relationships"]["FOLLOWED_BY"] == 1
    assert ("V301", "V302") in metrics["expected_transitions"]


def test_verify_node_counts_matching():
    """Matching node counts must report PASS with 0 errors."""
    mock_session = MagicMock()
    mock_session.run.return_value.data.return_value = [
        {"label": "Patient", "count": 50},
        {"label": "Doctor", "count": 10},
    ]

    expected = {"Patient": 50, "Doctor": 10}
    comp, errors = verify_node_counts(mock_session, expected)

    assert len(errors) == 0
    assert comp["Patient"]["status"] == "PASS"
    assert comp["Doctor"]["status"] == "PASS"


def test_verify_node_counts_mismatch():
    """Missing or unexpected nodes must be flagged as FAIL with errors."""
    mock_session = MagicMock()
    mock_session.run.return_value.data.return_value = [
        {"label": "Patient", "count": 48},  # 2 missing
        {"label": "GhostNode", "count": 5},  # Unexpected
    ]

    expected = {"Patient": 50, "Doctor": 10}
    comp, errors = verify_node_counts(mock_session, expected)

    assert len(errors) == 3  # Patient diff, Doctor missing, GhostNode extra
    assert comp["Patient"]["status"] == "FAIL"
    assert comp["Doctor"]["status"] == "FAIL"
    assert comp["GhostNode"]["status"] == "FAIL"


def test_verify_relationship_counts_mismatch():
    """Relationship count discrepancy must trigger FAIL."""
    mock_session = MagicMock()
    mock_session.run.return_value.data.return_value = [
        {"rel_type": "HAD_VISIT", "count": 140},  # Expected 146
    ]

    expected = {"HAD_VISIT": 146}
    comp, errors = verify_relationship_counts(mock_session, expected)

    assert len(errors) == 1
    assert comp["HAD_VISIT"]["status"] == "FAIL"
    assert comp["HAD_VISIT"]["difference"] == -6


def test_verify_trajectories_cross_patient():
    """A FOLLOWED_BY relationship between two different patients must trigger error."""
    mock_session = MagicMock()
    mock_session.run.return_value.data.return_value = [
        {
            "v1": "V301", "v2": "V303",
            "p1": "P101", "p2": "P102",  # Different patients
            "d1": "2023-01-10", "d2": "2023-03-01"
        }
    ]

    expected_transitions = {("V301", "V302")}
    valid, errors = verify_trajectories(mock_session, expected_transitions)

    assert valid is False
    assert any("Cross-patient" in err for err in errors)


def test_verify_trajectories_non_chronological():
    """A FOLLOWED_BY relationship pointing backwards in time must trigger error."""
    mock_session = MagicMock()
    mock_session.run.return_value.data.return_value = [
        {
            "v1": "V302", "v2": "V301",
            "p1": "P101", "p2": "P101",
            "d1": "2023-02-15", "d2": "2023-01-10"  # Reversed dates
        }
    ]

    expected_transitions = {("V301", "V302")}
    valid, errors = verify_trajectories(mock_session, expected_transitions)

    assert valid is False
    assert any("Non-chronological" in err for err in errors)


def test_verify_constraints_detection():
    """Schema inspection must flag the Diagnosis diagnosis_id vs condition mismatch."""
    mock_session = MagicMock()
    mock_session.run.return_value.data.return_value = [
        {
            "name": "unique_diagnosis_id",
            "labelsOrTypes": ["Diagnosis"],
            "properties": ["diagnosis_id"]
        }
    ]

    info, warnings = verify_constraints(mock_session)
    assert info["mismatch_detected"] is True
    assert len(warnings) == 1
    assert "Schema Mismatch Identified" in warnings[0]


def test_verify_live_graph_connection_failure():
    """verify_live_graph must handle connection failures gracefully without crashing."""
    mock_driver = MagicMock()
    mock_driver.verify_connectivity.side_effect = Exception("AuraDB unreachable")

    report = verify_live_graph(driver=mock_driver)
    assert report["success"] is False
    assert "Failed to connect" in report["error"]
    assert report["status"] == "FAIL"
