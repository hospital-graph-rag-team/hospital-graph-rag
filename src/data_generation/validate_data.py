import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

# Resolve default raw data directory relative to repository root
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

# Expected dataset schemas based on core and clinical generators
DATASET_SCHEMAS = {
    "patients.csv": {
        "required_columns": ["patient_id", "name", "dob", "gender"],
        "primary_key": "patient_id",
    },
    "doctors.csv": {
        "required_columns": ["doctor_id", "name", "specialty"],
        "primary_key": "doctor_id",
    },
    "visits.csv": {
        "required_columns": ["visit_id", "patient_id", "doctor_id", "visit_date", "admission_type"],
        "primary_key": "visit_id",
        "foreign_keys": [
            ("patient_id", "patients.csv", "patient_id"),
            ("doctor_id", "doctors.csv", "doctor_id"),
        ],
    },
    "diagnoses.csv": {
        "required_columns": ["diagnosis_id", "visit_id", "condition", "status"],
        "primary_key": "diagnosis_id",
        "foreign_keys": [
            ("visit_id", "visits.csv", "visit_id"),
        ],
    },
    "medications.csv": {
        "required_columns": ["prescription_id", "visit_id", "medication_name", "dosage", "is_effective"],
        "primary_key": "prescription_id",
        "foreign_keys": [
            ("visit_id", "visits.csv", "visit_id"),
        ],
    },
    "lab_tests.csv": {
        "required_columns": ["test_id", "visit_id", "test_name", "value", "unit"],
        "primary_key": "test_id",
        "foreign_keys": [
            ("visit_id", "visits.csv", "visit_id"),
        ],
    },
}

# Domain categorical domains and expected mappings from generators
ALLOWED_GENDERS = {"M", "F"}
ALLOWED_ADMISSION_TYPES = {"Outpatient", "Emergency", "Inpatient", "Follow-up"}
ALLOWED_SPECIALTIES = {
    "Cardiology", "Internal Medicine", "Neurology", "Orthopedics",
    "Endocrinology", "Pulmonology", "Gastroenterology", "General Practice"
}
ALLOWED_CONDITIONS = {"Type 2 Diabetes", "Hypertension", "Hyperlipidemia"}
ALLOWED_STATUSES = {"Active", "Resolved"}
ALLOWED_DOSAGES = {"Standard", "Low", "High"}

EXPECTED_LAB_UNITS = {
    "HbA1c": "%",
    "Systolic BP": "mmHg",
    "LDL Cholesterol": "mg/dL",
}


def _check_empty_or_whitespace(series: pd.Series) -> int:
    """Returns count of null, empty, or whitespace-only string values in a Series."""
    if series.empty:
        return 0
    is_na = series.isna()
    is_whitespace = series.astype(str).str.strip().eq("")
    return int((is_na | is_whitespace).sum())


def validate_datasets(
    data_dir: Optional[Path | str] = None,
    raise_on_error: bool = True
) -> Dict[str, Any]:
    """
    Validates all 6 core and clinical CSV datasets for schema structure,
    primary/foreign key integrity, missing values, data types, temporal order,
    and clinical coverage.
    """
    data_path = Path(data_dir) if data_dir else DEFAULT_DATA_DIR

    results: Dict[str, Dict[str, Any]] = {
        name: {
            "record_count": 0,
            "errors": [],
            "warnings": [],
            "duplicate_id_count": 0,
            "missing_val_count": 0,
            "orphan_count": 0,
            "status": "PENDING"
        }
        for name in DATASET_SCHEMAS
    }

    dfs: Dict[str, pd.DataFrame] = {}
    all_structural_errors: List[str] = []
    all_warnings: List[str] = []

    # ---------------------------------------------------------
    # 1. Dataset Structure: Existence, Required Columns, Empty
    # ---------------------------------------------------------
    for filename, schema in DATASET_SCHEMAS.items():
        file_path = data_path / filename
        res = results[filename]

        if not file_path.exists():
            msg = f"Missing required dataset file: {file_path}"
            res["errors"].append(msg)
            all_structural_errors.append(msg)
            res["status"] = "FAILED"
            continue

        try:
            df = pd.read_csv(file_path, dtype=str)
        except Exception as e:
            msg = f"Failed to parse CSV file {filename}: {e}"
            res["errors"].append(msg)
            all_structural_errors.append(msg)
            res["status"] = "FAILED"
            continue

        res["record_count"] = len(df)
        dfs[filename] = df

        if len(df) == 0:
            msg = f"{filename}: Dataset is empty (0 records)."
            res["errors"].append(msg)
            all_structural_errors.append(msg)

        # Check required columns
        missing_cols = set(schema["required_columns"]) - set(df.columns)
        if missing_cols:
            msg = f"{filename}: Missing required column(s): {sorted(list(missing_cols))}"
            res["errors"].append(msg)
            all_structural_errors.append(msg)

        # Detect unexpected schema changes without dropping columns
        extra_cols = set(df.columns) - set(schema["required_columns"])
        if extra_cols:
            w_msg = f"{filename}: Unexpected column(s) detected: {sorted(list(extra_cols))}"
            res["warnings"].append(w_msg)
            all_warnings.append(w_msg)

    # If any file failed to load or has missing columns, mark status
    for name in DATASET_SCHEMAS:
        if results[name]["errors"]:
            results[name]["status"] = "FAILED"

    # If critical files are missing, abort early
    if "patients.csv" not in dfs or "visits.csv" not in dfs:
        total_errors = len(all_structural_errors)
        total_warnings = len(all_warnings)
        report = {
            "is_valid": total_errors == 0,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "datasets": results,
            "all_errors": all_structural_errors,
            "all_warnings": all_warnings,
        }
        if raise_on_error and total_errors > 0:
            raise ValueError(f"Data validation failed with {total_errors} structural error(s):\n" + "\n".join(all_structural_errors))
        return report

    # ---------------------------------------------------------
    # 2. Primary Key Integrity & Missing Values
    # ---------------------------------------------------------
    for filename, df in dfs.items():
        res = results[filename]
        schema = DATASET_SCHEMAS[filename]
        pk_col = schema["primary_key"]

        if pk_col in df.columns:
            # Check empty/null/whitespace in PK
            pk_empty = _check_empty_or_whitespace(df[pk_col])
            if pk_empty > 0:
                msg = f"{filename}: Primary key '{pk_col}' contains {pk_empty} empty or whitespace value(s)."
                res["errors"].append(msg)
                all_structural_errors.append(msg)
                res["missing_val_count"] += pk_empty

            # Check duplicates in PK
            duplicates = df[df[pk_col].duplicated(keep=False)]
            dup_count = len(duplicates)
            if dup_count > 0:
                sample_dups = list(duplicates[pk_col].dropna().unique())[:3]
                msg = f"{filename}: Primary key '{pk_col}' contains {dup_count} duplicate rows (samples: {sample_dups})."
                res["errors"].append(msg)
                all_structural_errors.append(msg)
                res["duplicate_id_count"] = dup_count

        # Check missing values across all required columns
        for col in schema["required_columns"]:
            if col in df.columns and col != pk_col:
                missing_cnt = _check_empty_or_whitespace(df[col])
                if missing_cnt > 0:
                    msg = f"{filename}: Column '{col}' contains {missing_cnt} null or empty value(s)."
                    res["errors"].append(msg)
                    all_structural_errors.append(msg)
                    res["missing_val_count"] += missing_cnt

    # ---------------------------------------------------------
    # 3. Foreign Key Integrity
    # ---------------------------------------------------------
    for filename, df in dfs.items():
        res = results[filename]
        schema = DATASET_SCHEMAS[filename]
        foreign_keys = schema.get("foreign_keys", [])

        for fk_col, parent_file, parent_pk in foreign_keys:
            if fk_col in df.columns and parent_file in dfs and parent_pk in dfs[parent_file].columns:
                parent_df = dfs[parent_file]
                child_keys = set(df[fk_col].dropna().str.strip())
                parent_keys = set(parent_df[parent_pk].dropna().str.strip())

                orphans = child_keys - parent_keys
                if orphans:
                    sample_orphans = sorted(list(orphans))[:5]
                    msg = (
                        f"{filename}: Foreign key '{fk_col}' has {len(orphans)} orphan reference(s) "
                        f"not found in {parent_file}('{parent_pk}'): {sample_orphans}"
                    )
                    res["errors"].append(msg)
                    all_structural_errors.append(msg)
                    res["orphan_count"] += len(orphans)

    # ---------------------------------------------------------
    # 4. Data Types and Domain Value Checks
    # ---------------------------------------------------------
    # A. Date validation
    if "patients.csv" in dfs and "dob" in dfs["patients.csv"].columns:
        dob_raw = dfs["patients.csv"]["dob"]
        parsed_dob = pd.to_datetime(dob_raw, format="%Y-%m-%d", errors="coerce")
        invalid_dob_cnt = int(parsed_dob.isna().sum())
        if invalid_dob_cnt > 0:
            msg = f"patients.csv: 'dob' contains {invalid_dob_cnt} invalid date value(s) (expected YYYY-MM-DD)."
            results["patients.csv"]["errors"].append(msg)
            all_structural_errors.append(msg)

    if "visits.csv" in dfs and "visit_date" in dfs["visits.csv"].columns:
        vdate_raw = dfs["visits.csv"]["visit_date"]
        parsed_vdate = pd.to_datetime(vdate_raw, format="%Y-%m-%d", errors="coerce")
        invalid_vdate_cnt = int(parsed_vdate.isna().sum())
        if invalid_vdate_cnt > 0:
            msg = f"visits.csv: 'visit_date' contains {invalid_vdate_cnt} invalid date value(s) (expected YYYY-MM-DD)."
            results["visits.csv"]["errors"].append(msg)
            all_structural_errors.append(msg)

    # B. Categorical domains
    if "patients.csv" in dfs and "gender" in dfs["patients.csv"].columns:
        invalid_genders = set(dfs["patients.csv"]["gender"].dropna().str.strip()) - ALLOWED_GENDERS
        if invalid_genders:
            msg = f"patients.csv: 'gender' contains unexpected value(s): {invalid_genders} (expected {ALLOWED_GENDERS})."
            results["patients.csv"]["errors"].append(msg)
            all_structural_errors.append(msg)

    if "doctors.csv" in dfs and "specialty" in dfs["doctors.csv"].columns:
        invalid_specialties = set(dfs["doctors.csv"]["specialty"].dropna().str.strip()) - ALLOWED_SPECIALTIES
        if invalid_specialties:
            w_msg = f"doctors.csv: 'specialty' contains value(s) outside generator dictionary: {invalid_specialties}."
            results["doctors.csv"]["warnings"].append(w_msg)
            all_warnings.append(w_msg)

    if "visits.csv" in dfs and "admission_type" in dfs["visits.csv"].columns:
        invalid_admissions = set(dfs["visits.csv"]["admission_type"].dropna().str.strip()) - ALLOWED_ADMISSION_TYPES
        if invalid_admissions:
            w_msg = f"visits.csv: 'admission_type' contains value(s) outside generator dictionary: {invalid_admissions}."
            results["visits.csv"]["warnings"].append(w_msg)
            all_warnings.append(w_msg)

    if "diagnoses.csv" in dfs and "condition" in dfs["diagnoses.csv"].columns:
        invalid_conditions = set(dfs["diagnoses.csv"]["condition"].dropna().str.strip()) - ALLOWED_CONDITIONS
        if invalid_conditions:
            w_msg = f"diagnoses.csv: 'condition' contains value(s) outside known profiles: {invalid_conditions}."
            results["diagnoses.csv"]["warnings"].append(w_msg)
            all_warnings.append(w_msg)

    if "medications.csv" in dfs and "is_effective" in dfs["medications.csv"].columns:
        raw_eff = dfs["medications.csv"]["is_effective"].dropna().astype(str).str.strip().str.lower()
        invalid_eff = raw_eff[~raw_eff.isin(["true", "false", "1", "0"])]
        if len(invalid_eff) > 0:
            sample_invalid = list(invalid_eff.unique())[:3]
            msg = f"medications.csv: 'is_effective' contains {len(invalid_eff)} non-boolean value(s) (samples: {sample_invalid})."
            results["medications.csv"]["errors"].append(msg)
            all_structural_errors.append(msg)

    # C. Laboratory test numeric and finite values, test name and unit compatibility
    if "lab_tests.csv" in dfs:
        lab_df = dfs["lab_tests.csv"]
        if "value" in lab_df.columns:
            numeric_vals = pd.to_numeric(lab_df["value"], errors="coerce")
            non_numeric = numeric_vals.isna()
            non_finite = np.isinf(numeric_vals.fillna(0))
            invalid_vals_cnt = int((non_numeric | non_finite).sum())
            if invalid_vals_cnt > 0:
                msg = f"lab_tests.csv: 'value' contains {invalid_vals_cnt} non-numeric or non-finite reading(s)."
                results["lab_tests.csv"]["errors"].append(msg)
                all_structural_errors.append(msg)

        if "test_name" in lab_df.columns and "unit" in lab_df.columns:
            for _, row in lab_df.iterrows():
                tname = str(row.get("test_name", "")).strip()
                tunit = str(row.get("unit", "")).strip()
                if tname in EXPECTED_LAB_UNITS:
                    expected_unit = EXPECTED_LAB_UNITS[tname]
                    if tunit != expected_unit:
                        msg = (
                            f"lab_tests.csv: Incompatible unit for test '{tname}': "
                            f"found '{tunit}', expected '{expected_unit}'."
                        )
                        results["lab_tests.csv"]["errors"].append(msg)
                        all_structural_errors.append(msg)
                        break  # Report once per validation run

    # ---------------------------------------------------------
    # 5. Temporal Integrity
    # ---------------------------------------------------------
    if "visits.csv" in dfs and "patients.csv" in dfs:
        v_df = dfs["visits.csv"]
        p_df = dfs["patients.csv"]

        if "patient_id" in v_df.columns and "visit_date" in v_df.columns and "dob" in p_df.columns:
            merged = v_df.merge(p_df[["patient_id", "dob"]], on="patient_id", how="inner")
            v_dates = pd.to_datetime(merged["visit_date"], format="%Y-%m-%d", errors="coerce")
            p_dobs = pd.to_datetime(merged["dob"], format="%Y-%m-%d", errors="coerce")

            valid_mask = v_dates.notna() & p_dobs.notna()
            before_birth = merged[valid_mask & (v_dates < p_dobs)]
            if len(before_birth) > 0:
                sample_cases = list(before_birth[["patient_id", "visit_id", "visit_date", "dob"]].to_dict(orient="records"))[:2]
                msg = f"visits.csv: Found {len(before_birth)} visit(s) occurring before patient date of birth (samples: {sample_cases})."
                results["visits.csv"]["errors"].append(msg)
                all_structural_errors.append(msg)

        # Check for multiple visits on the same date for the same patient (duplicate/ambiguous dates)
        if "patient_id" in v_df.columns and "visit_date" in v_df.columns:
            same_day_dups = v_df[v_df.duplicated(subset=["patient_id", "visit_date"], keep=False)]
            if len(same_day_dups) > 0:
                patient_dups = list(same_day_dups["patient_id"].unique())[:3]
                w_msg = f"visits.csv: Detected {len(same_day_dups)} visit encounters on identical dates for same patient (samples: {patient_dups})."
                results["visits.csv"]["warnings"].append(w_msg)
                all_warnings.append(w_msg)

        # Chronological ordering check: verify whether CSV physical row order matches chronological trajectory
        if "patient_id" in v_df.columns and "visit_date" in v_df.columns:
            unsorted_patient_count = 0
            v_parsed_dates = pd.to_datetime(v_df["visit_date"], format="%Y-%m-%d", errors="coerce")
            temp_df = v_df.copy()
            temp_df["parsed_date"] = v_parsed_dates

            for pid, group in temp_df.groupby("patient_id", sort=False):
                # Valid dates only
                dates = group["parsed_date"].dropna().tolist()
                if len(dates) > 1:
                    if not all(dates[i] <= dates[i + 1] for i in range(len(dates) - 1)):
                        unsorted_patient_count += 1

            if unsorted_patient_count > 0:
                w_msg = (
                    f"visits.csv: {unsorted_patient_count} patient(s) have visits that are not in chronological physical row order. "
                    "Trajectory analysis should sort by visit_date ASC and visit_id ASC."
                )
                results["visits.csv"]["warnings"].append(w_msg)
                all_warnings.append(w_msg)

    # ---------------------------------------------------------
    # 6. Clinical Dataset Coverage
    # ---------------------------------------------------------
    if "visits.csv" in dfs:
        v_df = dfs["visits.csv"]
        if "visit_id" in v_df.columns:
            all_visits = set(v_df["visit_id"].dropna().str.strip())

            # A. Diagnoses coverage
            if "diagnoses.csv" in dfs and "visit_id" in dfs["diagnoses.csv"].columns:
                diag_visits = set(dfs["diagnoses.csv"]["visit_id"].dropna().str.strip())
                missing_diag = all_visits - diag_visits
                if missing_diag:
                    w_msg = f"diagnoses.csv: {len(missing_diag)} visit(s) have no associated diagnosis records."
                    results["diagnoses.csv"]["warnings"].append(w_msg)
                    all_warnings.append(w_msg)

                # Distribution warning (if != 1 record per visit)
                diag_counts = dfs["diagnoses.csv"]["visit_id"].value_counts()
                multi_diag = (diag_counts > 1).sum()
                if multi_diag > 0:
                    w_msg = f"diagnoses.csv: {multi_diag} visit(s) have multiple diagnosis records."
                    results["diagnoses.csv"]["warnings"].append(w_msg)
                    all_warnings.append(w_msg)

            # B. Medications coverage
            if "medications.csv" in dfs and "visit_id" in dfs["medications.csv"].columns:
                med_visits = set(dfs["medications.csv"]["visit_id"].dropna().str.strip())
                missing_med = all_visits - med_visits
                if missing_med:
                    w_msg = f"medications.csv: {len(missing_med)} visit(s) have no associated medication records."
                    results["medications.csv"]["warnings"].append(w_msg)
                    all_warnings.append(w_msg)

                med_counts = dfs["medications.csv"]["visit_id"].value_counts()
                multi_med = (med_counts > 1).sum()
                if multi_med > 0:
                    w_msg = f"medications.csv: {multi_med} visit(s) have multiple medication records."
                    results["medications.csv"]["warnings"].append(w_msg)
                    all_warnings.append(w_msg)

            # C. Lab tests coverage
            if "lab_tests.csv" in dfs and "visit_id" in dfs["lab_tests.csv"].columns:
                lab_visits = set(dfs["lab_tests.csv"]["visit_id"].dropna().str.strip())
                missing_lab = all_visits - lab_visits
                if missing_lab:
                    w_msg = f"lab_tests.csv: {len(missing_lab)} visit(s) have no associated lab test records."
                    results["lab_tests.csv"]["warnings"].append(w_msg)
                    all_warnings.append(w_msg)

                lab_counts = dfs["lab_tests.csv"]["visit_id"].value_counts()
                multi_lab = (lab_counts > 1).sum()
                if multi_lab > 0:
                    w_msg = f"lab_tests.csv: {multi_lab} visit(s) have multiple lab test records."
                    results["lab_tests.csv"]["warnings"].append(w_msg)
                    all_warnings.append(w_msg)

    # ---------------------------------------------------------
    # 7. Final Status Determination
    # ---------------------------------------------------------
    for name in DATASET_SCHEMAS:
        if results[name]["errors"]:
            results[name]["status"] = "FAILED"
        else:
            results[name]["status"] = "PASSED"

    total_errors = len(all_structural_errors)
    total_warnings = len(all_warnings)
    is_valid = total_errors == 0

    report = {
        "is_valid": is_valid,
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "datasets": results,
        "all_errors": all_structural_errors,
        "all_warnings": all_warnings,
    }

    print_validation_summary(report)

    if raise_on_error and total_errors > 0:
        raise ValueError(f"Data validation failed with {total_errors} structural error(s):\n" + "\n".join(all_structural_errors))

    return report


def print_validation_summary(report: Dict[str, Any]) -> None:
    """Prints a structured ASCII report of dataset validation results."""
    print("\n" + "=" * 90)
    print("                 CLINICAL GRAPH RAG — COMPREHENSIVE DATA VALIDATION REPORT")
    print("=" * 90)
    print(f"{'Dataset':<18} | {'Rows':<6} | {'Errors':<6} | {'Warns':<6} | {'Dup IDs':<7} | {'Missing':<7} | {'Orphans':<7} | {'Status':<6}")
    print("-" * 90)

    for filename, r in report["datasets"].items():
        print(
            f"{filename:<18} | "
            f"{r['record_count']:<6} | "
            f"{len(r['errors']):<6} | "
            f"{len(r['warnings']):<6} | "
            f"{r['duplicate_id_count']:<7} | "
            f"{r['missing_val_count']:<7} | "
            f"{r['orphan_count']:<7} | "
            f"{r['status']:<6}"
        )

    print("-" * 90)
    status_str = "PASSED" if report["is_valid"] else "FAILED"
    print(
        f"TOTALS: Errors = {report['total_errors']}, "
        f"Warnings = {report['total_warnings']} | "
        f"Overall Status: {status_str}"
    )
    print("=" * 90)

    if report["all_errors"]:
        print("\n[CRITICAL STRUCTURAL ERRORS]")
        for err in report["all_errors"]:
            print(f"  ✗ {err}")

    if report["all_warnings"]:
        print("\n[DATASET-SPECIFIC WARNINGS]")
        for w in report["all_warnings"]:
            print(f"  ⚠ {w}")
    print()


if __name__ == "__main__":
    validation_report = validate_datasets(raise_on_error=False)
    if not validation_report["is_valid"]:
        sys.exit(1)
    sys.exit(0)
