import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

def validate_datasets():
    p_path = DATA_DIR / "patients.csv"
    d_path = DATA_DIR / "doctors.csv"
    v_path = DATA_DIR / "visits.csv"

    for path in [p_path, d_path, v_path]:
        if not path.exists():
            raise FileNotFoundError(f"Missing expected CSV: {path}")

    patients = pd.read_csv(p_path)
    doctors = pd.read_csv(d_path)
    visits = pd.read_csv(v_path)

    print("--- Running Data Validation Checks ---")

    # 1. Null Checks
    assert not patients.isnull().any().any(), "Error: Null values found in patients.csv"
    assert not doctors.isnull().any().any(), "Error: Null values found in doctors.csv"
    assert not visits.isnull().any().any(), "Error: Null values found in visits.csv"
    print("✓ Check passed: No missing values.")

    # 2. Unique Key Checks
    assert patients["patient_id"].is_unique, "Error: Duplicate patient_id found"
    assert doctors["doctor_id"].is_unique, "Error: Duplicate doctor_id found"
    assert visits["visit_id"].is_unique, "Error: Duplicate visit_id found"
    print("✓ Check passed: Primary keys are unique.")

    # 3. Foreign Key Checks
    orphan_patients = set(visits["patient_id"]) - set(patients["patient_id"])
    assert len(orphan_patients) == 0, f"Error: visits reference non-existent patients: {orphan_patients}"
    
    orphan_doctors = set(visits["doctor_id"]) - set(doctors["doctor_id"])
    assert len(orphan_doctors) == 0, f"Error: visits reference non-existent doctors: {orphan_doctors}"
    print("✓ Check passed: All foreign keys match valid parent records.")

    # 4. Date Format Checks
    pd.to_datetime(patients["dob"], format="%Y-%m-%d", errors="raise")
    pd.to_datetime(visits["visit_date"], format="%Y-%m-%d", errors="raise")
    print("✓ Check passed: Date formats are valid YYYY-MM-DD.")

    print("\nAll datasets validated successfully! Ready for Person 2 and Phase 3.")

if __name__ == "__main__":
    validate_datasets()