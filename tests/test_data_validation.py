import pytest
import pandas as pd
from pathlib import Path
import sys

# Add src to Python path
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from data_generation.validate_data import validate_datasets


@pytest.fixture
def synthetic_data_dir(tmp_path):
    """Creates a complete and valid synthetic hospital dataset for testing."""
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


def test_valid_datasets(synthetic_data_dir):
    """Valid synthetic dataset should pass with 0 errors and 0 warnings."""
    report = validate_datasets(synthetic_data_dir, raise_on_error=True)
    assert report["is_valid"] is True
    assert report["total_errors"] == 0
    assert report["total_warnings"] == 0


def test_duplicate_primary_keys(synthetic_data_dir):
    """Duplicate primary key in patients.csv must be flagged as structural error."""
    df = pd.read_csv(synthetic_data_dir / "patients.csv", dtype=str)
    df.loc[1, "patient_id"] = "P101"  # Duplicate P101
    df.to_csv(synthetic_data_dir / "patients.csv", index=False)

    report = validate_datasets(synthetic_data_dir, raise_on_error=False)
    assert report["is_valid"] is False
    assert report["datasets"]["patients.csv"]["duplicate_id_count"] > 0
    assert any("duplicate" in err.lower() for err in report["all_errors"])


def test_missing_primary_keys(synthetic_data_dir):
    """Empty or whitespace-only primary key in doctors.csv must trigger error."""
    df = pd.read_csv(synthetic_data_dir / "doctors.csv", dtype=str)
    df.loc[0, "doctor_id"] = "   "  # Whitespace only
    df.to_csv(synthetic_data_dir / "doctors.csv", index=False)

    report = validate_datasets(synthetic_data_dir, raise_on_error=False)
    assert report["is_valid"] is False
    assert any("empty or whitespace" in err.lower() for err in report["all_errors"])


def test_orphan_patient_references(synthetic_data_dir):
    """Visit referencing non-existent patient must be flagged as orphan error."""
    df = pd.read_csv(synthetic_data_dir / "visits.csv", dtype=str)
    df.loc[0, "patient_id"] = "P999"  # Non-existent
    df.to_csv(synthetic_data_dir / "visits.csv", index=False)

    report = validate_datasets(synthetic_data_dir, raise_on_error=False)
    assert report["is_valid"] is False
    assert report["datasets"]["visits.csv"]["orphan_count"] > 0
    assert any("orphan" in err.lower() for err in report["all_errors"])


def test_orphan_doctor_references(synthetic_data_dir):
    """Visit referencing non-existent doctor must be flagged as orphan error."""
    df = pd.read_csv(synthetic_data_dir / "visits.csv", dtype=str)
    df.loc[0, "doctor_id"] = "DOC999"  # Non-existent
    df.to_csv(synthetic_data_dir / "visits.csv", index=False)

    report = validate_datasets(synthetic_data_dir, raise_on_error=False)
    assert report["is_valid"] is False
    assert report["datasets"]["visits.csv"]["orphan_count"] > 0
    assert any("orphan" in err.lower() for err in report["all_errors"])


def test_orphan_clinical_visit_references(synthetic_data_dir):
    """Diagnosis referencing non-existent visit must be flagged as orphan error."""
    df = pd.read_csv(synthetic_data_dir / "diagnoses.csv", dtype=str)
    df.loc[0, "visit_id"] = "V999"  # Non-existent
    df.to_csv(synthetic_data_dir / "diagnoses.csv", index=False)

    report = validate_datasets(synthetic_data_dir, raise_on_error=False)
    assert report["is_valid"] is False
    assert report["datasets"]["diagnoses.csv"]["orphan_count"] > 0
    assert any("orphan" in err.lower() for err in report["all_errors"])


def test_missing_required_columns(synthetic_data_dir):
    """Omitting required column must cause structural validation error."""
    df = pd.read_csv(synthetic_data_dir / "patients.csv", dtype=str)
    df = df.drop(columns=["gender"])
    df.to_csv(synthetic_data_dir / "patients.csv", index=False)

    report = validate_datasets(synthetic_data_dir, raise_on_error=False)
    assert report["is_valid"] is False
    assert any("missing required column" in err.lower() for err in report["all_errors"])


def test_missing_required_values(synthetic_data_dir):
    """Empty or null values in required columns must trigger error."""
    df = pd.read_csv(synthetic_data_dir / "visits.csv", dtype=str)
    df.loc[0, "admission_type"] = ""
    df.to_csv(synthetic_data_dir / "visits.csv", index=False)

    report = validate_datasets(synthetic_data_dir, raise_on_error=False)
    assert report["is_valid"] is False
    assert any("null or empty" in err.lower() for err in report["all_errors"])


def test_invalid_dates(synthetic_data_dir):
    """Invalid date strings that do not follow YYYY-MM-DD must fail."""
    df = pd.read_csv(synthetic_data_dir / "visits.csv", dtype=str)
    df.loc[0, "visit_date"] = "2023-02-31"  # Invalid calendar day
    df.to_csv(synthetic_data_dir / "visits.csv", index=False)

    report = validate_datasets(synthetic_data_dir, raise_on_error=False)
    assert report["is_valid"] is False
    assert any("invalid date" in err.lower() for err in report["all_errors"])


def test_visits_before_patient_birth_dates(synthetic_data_dir):
    """Visit occurring before patient's date of birth must trigger error."""
    df = pd.read_csv(synthetic_data_dir / "visits.csv", dtype=str)
    df.loc[0, "visit_date"] = "1975-01-01"  # Patient P101 DOB is 1980-01-01
    df.to_csv(synthetic_data_dir / "visits.csv", index=False)

    report = validate_datasets(synthetic_data_dir, raise_on_error=False)
    assert report["is_valid"] is False
    assert any("occurring before patient date of birth" in err.lower() for err in report["all_errors"])


def test_invalid_laboratory_values(synthetic_data_dir):
    """Non-numeric string in lab value must trigger error."""
    df = pd.read_csv(synthetic_data_dir / "lab_tests.csv", dtype=str)
    df.loc[0, "value"] = "HIGH"
    df.to_csv(synthetic_data_dir / "lab_tests.csv", index=False)

    report = validate_datasets(synthetic_data_dir, raise_on_error=False)
    assert report["is_valid"] is False
    assert any("non-numeric" in err.lower() for err in report["all_errors"])


def test_nonfinite_laboratory_values(synthetic_data_dir):
    """Infinity value in lab test must trigger error."""
    df = pd.read_csv(synthetic_data_dir / "lab_tests.csv", dtype=str)
    df.loc[0, "value"] = "inf"
    df.to_csv(synthetic_data_dir / "lab_tests.csv", index=False)

    report = validate_datasets(synthetic_data_dir, raise_on_error=False)
    assert report["is_valid"] is False
    assert any("non-finite" in err.lower() for err in report["all_errors"])


def test_invalid_boolean_values(synthetic_data_dir):
    """Non-boolean value in medication effectiveness must trigger error."""
    df = pd.read_csv(synthetic_data_dir / "medications.csv", dtype=str)
    df.loc[0, "is_effective"] = "unknown_status"
    df.to_csv(synthetic_data_dir / "medications.csv", index=False)

    report = validate_datasets(synthetic_data_dir, raise_on_error=False)
    assert report["is_valid"] is False
    assert any("non-boolean" in err.lower() for err in report["all_errors"])


def test_missing_clinical_records(synthetic_data_dir):
    """Visits without associated diagnosis records should trigger coverage warning without structural error."""
    df = pd.read_csv(synthetic_data_dir / "diagnoses.csv", dtype=str)
    df = df[df["visit_id"] != "V303"]  # Remove diagnosis for V303
    df.to_csv(synthetic_data_dir / "diagnoses.csv", index=False)

    report = validate_datasets(synthetic_data_dir, raise_on_error=False)
    # Warnings are emitted for coverage, but structural integrity remains valid
    assert report["is_valid"] is True
    assert report["total_warnings"] > 0
    assert any("no associated diagnosis records" in w.lower() for w in report["all_warnings"])


def test_unsorted_visit_dates(synthetic_data_dir):
    """Visits out of physical chronological row order should trigger warning but pass validation."""
    df = pd.read_csv(synthetic_data_dir / "visits.csv", dtype=str)
    # Swap row 0 (V301, 2023-01-10) and row 1 (V302, 2023-02-15) for patient P101
    row0 = df.iloc[0].to_dict()
    row1 = df.iloc[1].to_dict()
    df.iloc[0] = row1
    df.iloc[1] = row0
    df.to_csv(synthetic_data_dir / "visits.csv", index=False)

    report = validate_datasets(synthetic_data_dir, raise_on_error=False)
    assert report["is_valid"] is True
    assert report["total_warnings"] > 0
    assert any("chronological physical row order" in w.lower() for w in report["all_warnings"])


def test_laboratory_unit_inconsistencies(synthetic_data_dir):
    """Incompatible unit for test name (e.g. HbA1c with mg/dL) must trigger error."""
    df = pd.read_csv(synthetic_data_dir / "lab_tests.csv", dtype=str)
    df.loc[0, "unit"] = "mg/dL"  # HbA1c expected unit is %
    df.to_csv(synthetic_data_dir / "lab_tests.csv", index=False)

    report = validate_datasets(synthetic_data_dir, raise_on_error=False)
    assert report["is_valid"] is False
    assert any("incompatible unit" in err.lower() for err in report["all_errors"])
