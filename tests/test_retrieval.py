import pytest
import json
from datetime import date, datetime
from unittest.mock import MagicMock
import neo4j.time

from graph.retrieval import (
    serialize_neo4j_value,
    get_patient_history,
    get_best_medications_for_condition,
    get_patient_directory,
    get_patient_profile,
    get_patient_timeline,
    get_lab_trends,
    get_followup_comparison,
    get_medication_outcomes,
)


# =====================================================================
# 1. JSON Serialization Tests
# =====================================================================

def test_json_serialization_neo4j_types():
    """Verify that neo4j.time.Date, Python dates, and primitives serialize to valid JSON without default=str."""
    data = {
        "neo_date": neo4j.time.Date(2023, 8, 28),
        "py_date": date(2023, 1, 15),
        "py_datetime": datetime(2023, 1, 15, 10, 30, 0),
        "num_int": 42,
        "num_float": 183.1,
        "flag": True,
        "none_val": None,
        "nested_list": [
            {"date": neo4j.time.Date(2023, 9, 21), "val": 136.8}
        ]
    }

    serialized = serialize_neo4j_value(data)

    # Standard json.dumps should succeed without default=str
    json_output = json.dumps(serialized)
    assert isinstance(json_output, str)

    # Verify types preserved
    assert serialized["neo_date"] == "2023-08-28"
    assert serialized["py_date"] == "2023-01-15"
    assert serialized["py_datetime"] == "2023-01-15T10:30:00"
    assert serialized["num_int"] == 42
    assert serialized["num_float"] == 183.1
    assert serialized["flag"] is True
    assert serialized["none_val"] is None
    assert serialized["nested_list"][0]["val"] == 136.8
    assert serialized["nested_list"][0]["date"] == "2023-09-21"


# =====================================================================
# 2. Patient Directory Tests
# =====================================================================

def test_patient_directory_retrieval():
    """Verify patient directory ordering, fields, and JSON compatibility."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_session.run.return_value.data.return_value = [
        {"patient_id": "P101", "name": "James Jones", "dob": "1971-12-21", "gender": "M"},
        {"patient_id": "P102", "name": "Mary Smith", "dob": "1980-05-10", "gender": "F"},
    ]

    directory = get_patient_directory(driver=mock_driver)
    assert len(directory) == 2
    assert directory[0]["patient_id"] == "P101"
    assert directory[1]["patient_id"] == "P102"
    # Ensure json.dumps works directly
    assert json.dumps(directory) is not None


def test_patient_directory_empty():
    """Verify empty directory returns empty list."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.run.return_value.data.return_value = []

    directory = get_patient_directory(driver=mock_driver)
    assert directory == []


# =====================================================================
# 3. Patient Profile Tests
# =====================================================================

def test_patient_profile_found():
    """Verify patient profile correctly populates demographic and visit metadata."""
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
        "latest_visit_date": "2023-10-18",
    }
    mock_session.run.return_value.single.return_value = mock_record

    profile = get_patient_profile("P101", driver=mock_driver)
    assert profile is not None
    assert profile["patient_id"] == "P101"
    assert profile["visit_count"] == 3
    assert profile["first_visit_date"] == "2023-08-28"
    assert profile["latest_visit_date"] == "2023-10-18"


def test_patient_profile_not_found():
    """Verify nonexistent patient returns None."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.run.return_value.single.return_value = None

    profile = get_patient_profile("P999", driver=mock_driver)
    assert profile is None


# =====================================================================
# 4. Structured Patient Timeline Tests
# =====================================================================

def test_patient_timeline_chronological_and_nested():
    """Verify patient timeline retains nested entities without Cartesian product and sorts chronologically."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_session.run.return_value.data.return_value = [
        {
            "visit_id": "V301",
            "visit_date": "2023-08-28",
            "admission_type": "Inpatient",
            "doctor": {"doctor_id": "DOC207", "name": "Dr. Strange", "specialty": "Internal Medicine"},
            "diagnoses": [{"diagnosis_id": "D0001", "condition": "Hyperlipidemia", "status": "Active"}],
            "medications": [{"prescription_id": "RX0001", "medication_name": "Rosuvastatin", "dosage": "Standard", "is_effective": True}],
            "lab_tests": [{"test_id": "T0001", "test_name": "LDL Cholesterol", "value": 183.1, "unit": "mg/dL"}],
        },
        {
            "visit_id": "V302",
            "visit_date": "2023-09-21",
            "admission_type": "Follow-up",
            "doctor": {"doctor_id": "DOC207", "name": "Dr. Strange", "specialty": "Internal Medicine"},
            "diagnoses": [],  # Empty diagnosis record test
            "medications": [],
            "lab_tests": [{"test_id": "T0002", "test_name": "LDL Cholesterol", "value": 136.8, "unit": "mg/dL"}],
        }
    ]

    timeline = get_patient_timeline("P101", driver=mock_driver)
    assert len(timeline) == 2
    assert timeline[0]["visit_id"] == "V301"
    assert timeline[1]["visit_id"] == "V302"
    assert len(timeline[0]["diagnoses"]) == 1
    assert len(timeline[1]["diagnoses"]) == 0
    assert timeline[0]["lab_tests"][0]["value"] == 183.1
    # Check serialization
    assert json.dumps(timeline) is not None


def test_patient_timeline_empty():
    """Nonexistent patient returns empty list."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.run.return_value.data.return_value = []

    timeline = get_patient_timeline("P999", driver=mock_driver)
    assert timeline == []


# =====================================================================
# 5. Laboratory Trend Retrieval Tests
# =====================================================================

def test_lab_trends_multi_observation_calculation():
    """Verify initial, latest, delta, percentage, and direction calculations across multiple lab observations."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_session.run.return_value.data.return_value = [
        {"visit_id": "V301", "visit_date": "2023-01-10", "test_id": "T01", "test_name": "HbA1c", "value": 10.0, "unit": "%"},
        {"visit_id": "V302", "visit_date": "2023-02-15", "test_id": "T02", "test_name": "HbA1c", "value": 8.0, "unit": "%"},
        {"visit_id": "V303", "visit_date": "2023-03-20", "test_id": "T03", "test_name": "HbA1c", "value": 7.0, "unit": "%"},
    ]

    trends = get_lab_trends("P101", test_name="HbA1c", driver=mock_driver)
    assert len(trends) == 1
    trend = trends[0]
    assert trend["biomarker"] == "HbA1c"
    assert trend["unit"] == "%"
    assert trend["observation_count"] == 3
    assert trend["initial_value"] == 10.0
    assert trend["latest_value"] == 7.0
    assert trend["absolute_change"] == -3.0
    assert trend["percentage_change"] == -30.0
    assert trend["direction"] == "decreased"
    assert len(trend["observations"]) == 3


def test_lab_trends_single_observation():
    """Single observation does not establish a trend and should report direction='insufficient_data'."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_session.run.return_value.data.return_value = [
        {"visit_id": "V301", "visit_date": "2023-01-10", "test_id": "T01", "test_name": "Systolic BP", "value": 140.0, "unit": "mmHg"},
    ]

    trends = get_lab_trends("P101", test_name="Systolic BP", driver=mock_driver)
    assert len(trends) == 1
    trend = trends[0]
    assert trend["observation_count"] == 1
    assert trend["initial_value"] == 140.0
    assert trend["latest_value"] == 140.0
    assert trend["absolute_change"] == 0.0
    assert trend["percentage_change"] is None
    assert trend["direction"] == "insufficient_data"


def test_lab_trends_zero_initial_value():
    """Zero initial value must not raise ZeroDivisionError and should report percentage_change as None."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_session.run.return_value.data.return_value = [
        {"visit_id": "V301", "visit_date": "2023-01-10", "test_id": "T01", "test_name": "TestX", "value": 0.0, "unit": "mg/dL"},
        {"visit_id": "V302", "visit_date": "2023-02-10", "test_id": "T02", "test_name": "TestX", "value": 5.0, "unit": "mg/dL"},
    ]

    trends = get_lab_trends("P101", test_name="TestX", driver=mock_driver)
    assert len(trends) == 1
    trend = trends[0]
    assert trend["initial_value"] == 0.0
    assert trend["percentage_change"] is None
    assert trend["direction"] == "increased"


def test_lab_trends_multi_biomarkers_isolated():
    """Different biomarkers and units must remain in isolated trend groups without cross-contamination."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_session.run.return_value.data.return_value = [
        {"visit_id": "V301", "visit_date": "2023-01-10", "test_id": "T01", "test_name": "HbA1c", "value": 9.0, "unit": "%"},
        {"visit_id": "V301", "visit_date": "2023-01-10", "test_id": "T02", "test_name": "Systolic BP", "value": 150.0, "unit": "mmHg"},
    ]

    trends = get_lab_trends("P101", test_name=None, driver=mock_driver)
    assert len(trends) == 2
    biomarkers = [t["biomarker"] for t in trends]
    assert "HbA1c" in biomarkers
    assert "Systolic BP" in biomarkers


# =====================================================================
# 6. Follow-up Comparison Tests
# =====================================================================

def test_followup_comparison_structure():
    """Verify follow-up visit comparisons compute elapsed days and matched biomarker deltas."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_session.run.return_value.data.return_value = [
        {
            "v1_id": "V301",
            "v1_date": "2023-08-28",
            "v1_admission": "Inpatient",
            "v1_doctor": "Dr. Strange",
            "v2_id": "V302",
            "v2_date": "2023-09-21",
            "v2_admission": "Follow-up",
            "v2_doctor": "Dr. Strange",
            "v1_diagnoses": [{"diagnosis_id": "D001", "condition": "Hyperlipidemia", "status": "Active"}],
            "v2_diagnoses": [{"diagnosis_id": "D002", "condition": "Hyperlipidemia", "status": "Active"}],
            "v1_prescriptions": [{"prescription_id": "RX01", "medication_name": "Rosuvastatin", "dosage": "Standard", "is_effective": True}],
            "v2_prescriptions": [{"prescription_id": "RX02", "medication_name": "Rosuvastatin", "dosage": "Standard", "is_effective": True}],
            "v1_labs": [{"test_id": "T01", "test_name": "LDL Cholesterol", "value": 183.1, "unit": "mg/dL"}],
            "v2_labs": [{"test_id": "T02", "test_name": "LDL Cholesterol", "value": 136.8, "unit": "mg/dL"}],
        }
    ]

    comparisons = get_followup_comparison("P101", driver=mock_driver)
    assert len(comparisons) == 1
    comp = comparisons[0]
    assert comp["patient_id"] == "P101"
    assert comp["days_between"] == 24
    assert len(comp["lab_comparisons"]) == 1
    lab = comp["lab_comparisons"][0]
    assert lab["biomarker"] == "LDL Cholesterol"
    assert lab["v1_value"] == 183.1
    assert lab["v2_value"] == 136.8
    assert lab["absolute_change"] == -46.3
    assert lab["direction"] == "decreased"


def test_followup_comparison_empty():
    """Patient with no follow-up transitions returns empty list."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.run.return_value.data.return_value = []

    comparisons = get_followup_comparison("P999", driver=mock_driver)
    assert comparisons == []


# =====================================================================
# 7. Medication Outcome Analysis Tests
# =====================================================================

def test_medication_outcomes_aggregation():
    """Verify medication outcome analysis correctly separates transition counts from unique patient counts."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_session.run.return_value.data.return_value = [
        # Patient P101: 2 transitions on Metformin, both improved
        {"patient_id": "P101", "medication_name": "Metformin", "prescription_id": "RX1", "dosage": "Standard", "generator_is_effective": True,
         "v1_id": "V301", "v1_date": "2023-01-01", "v2_id": "V302", "v2_date": "2023-02-01", "t1_id": "T1", "biomarker": "HbA1c", "v1_value": 9.5, "unit": "%", "t2_id": "T2", "v2_value": 7.5},
        {"patient_id": "P101", "medication_name": "Metformin", "prescription_id": "RX2", "dosage": "Standard", "generator_is_effective": True,
         "v1_id": "V302", "v1_date": "2023-02-01", "v2_id": "V303", "v2_date": "2023-03-01", "t1_id": "T2", "biomarker": "HbA1c", "v1_value": 7.5, "unit": "%", "t2_id": "T3", "v2_value": 6.8},
        # Patient P102: 1 transition on Metformin, worsened
        {"patient_id": "P102", "medication_name": "Metformin", "prescription_id": "RX3", "dosage": "Standard", "generator_is_effective": False,
         "v1_id": "V304", "v1_date": "2023-01-15", "v2_id": "V305", "v2_date": "2023-02-15", "t1_id": "T4", "biomarker": "HbA1c", "v1_value": 8.0, "unit": "%", "t2_id": "T5", "v2_value": 8.5},
    ]

    outcomes = get_medication_outcomes("Type 2 Diabetes", driver=mock_driver)
    assert outcomes["condition"] == "Type 2 Diabetes"
    assert outcomes["biomarker"] == "HbA1c"
    assert outcomes["unit"] == "%"
    assert outcomes["total_eligible_transitions"] == 3
    assert outcomes["total_unique_patients"] == 2

    assert len(outcomes["medications"]) == 1
    med = outcomes["medications"][0]
    assert med["medication"] == "Metformin"
    assert med["eligible_transitions"] == 3
    assert med["unique_patient_count"] == 2
    assert med["improved_transitions"] == 2
    assert med["worsened_transitions"] == 1
    assert med["unchanged_transitions"] == 0
    assert med["betterment_rate_pct"] == 66.67
    assert len(med["evidence_sample"]) == 3


def test_medication_outcomes_unknown_condition():
    """Unknown condition returns zero transitions and empty medications without crashing."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.run.return_value.data.return_value = []

    outcomes = get_medication_outcomes("Unknown Disease", driver=mock_driver)
    assert outcomes["total_eligible_transitions"] == 0
    assert outcomes["total_unique_patients"] == 0
    assert outcomes["medications"] == []


# =====================================================================
# 8. Error Handling & Backward Compatibility Tests
# =====================================================================

def test_database_error_handling_not_silently_swallowed():
    """Database query execution failures should raise exceptions rather than masking errors as empty lists."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.run.side_effect = neo4j.exceptions.DatabaseError("Syntax or connection error")

    with pytest.raises(neo4j.exceptions.DatabaseError):
        get_patient_timeline("P101", driver=mock_driver)


def test_backward_compatible_functions():
    """Verify legacy Person 1 functions get_patient_history and get_best_medications_for_condition remain operational."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_rec1 = MagicMock()
    mock_rec1.data.return_value = {"visit_id": "V301", "doctor": "Dr. House", "diagnosis": "Diabetes"}
    mock_session.run.return_value = [mock_rec1]

    hist = get_patient_history("P101", driver=mock_driver)
    assert len(hist) == 1
    assert hist[0]["visit_id"] == "V301"

    mock_rec2 = MagicMock()
    mock_rec2.data.return_value = {"medication": "Metformin", "betterment_rate_pct": 80.0}
    mock_session.run.return_value = [mock_rec2]

    best_meds = get_best_medications_for_condition("Diabetes", driver=mock_driver)
    assert len(best_meds) == 1
    assert best_meds[0]["betterment_rate_pct"] == 80.0


def test_get_hospital_overview_stats():
    """Verify get_hospital_overview_stats parses totals, conditions, and admission types."""
    from src.graph.retrieval import get_hospital_overview_stats

    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_totals_record = MagicMock()
    mock_totals_record.__getitem__.side_effect = lambda key: {
        "total_nodes": 364,
        "total_relationships": 826,
        "total_patients": 50,
        "total_doctors": 10,
        "total_visits": 146,
        "total_diagnosis_records": 146,
        "total_prescription_records": 146,
        "total_lab_records": 146
    }
    mock_totals_res = MagicMock()
    mock_totals_res.single.return_value = mock_totals_record

    mock_conditions_res = [
        {"condition": "Hyperlipidemia", "patient_count": 20, "record_count": 54},
        {"condition": "Type 2 Diabetes", "patient_count": 15, "record_count": 45}
    ]
    mock_admission_res = [
        {"admission_type": "Follow-up", "count": 96},
        {"admission_type": "Outpatient", "count": 18}
    ]

    mock_session.run.side_effect = [
        mock_totals_res,
        mock_conditions_res,
        mock_admission_res
    ]

    stats = get_hospital_overview_stats(driver=mock_driver)
    assert stats["totals"]["total_patients"] == 50
    assert stats["totals"]["total_nodes"] == 364
    assert len(stats["conditions"]) == 2
    assert stats["conditions"][0]["condition"] == "Hyperlipidemia"
    assert len(stats["admission_types"]) == 2
    assert stats["admission_types"][0]["admission_type"] == "Follow-up"
