import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd

# Path configurations
ROOT_DIR = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = ROOT_DIR / "data" / "raw"

# Add src to path for imports
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from graph.connection import get_driver
except ModuleNotFoundError:
    from connection import get_driver


def derive_expected_metrics(data_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Derives expected node counts, relationship counts, and trajectory paths
    directly from the validated CSV source datasets.
    """
    path = Path(data_dir) if data_dir else RAW_DATA_DIR

    patients_df = pd.read_csv(path / "patients.csv")
    doctors_df = pd.read_csv(path / "doctors.csv")
    visits_df = pd.read_csv(path / "visits.csv")
    diagnoses_df = pd.read_csv(path / "diagnoses.csv")
    medications_df = pd.read_csv(path / "medications.csv")
    lab_tests_df = pd.read_csv(path / "lab_tests.csv")

    # 1. Expected Node Counts
    # Note: Diagnosis and Medication nodes are deduplicated by condition and medication_name
    expected_nodes = {
        "Patient": len(patients_df),
        "Doctor": len(doctors_df),
        "Visit": len(visits_df),
        "Diagnosis": diagnoses_df["condition"].nunique(),
        "Medication": medications_df["medication_name"].nunique(),
        "LabTest": len(lab_tests_df),
    }

    # 2. Expected Relationship Counts
    # Calculate FOLLOWED_BY dynamically: sum of (visit_count - 1) for each patient
    visits_sorted = visits_df.sort_values(by=["patient_id", "visit_date", "visit_id"])
    expected_followed_by = 0
    expected_transitions = set()

    for pid, group in visits_sorted.groupby("patient_id"):
        vids = group["visit_id"].tolist()
        if len(vids) > 1:
            expected_followed_by += len(vids) - 1
            for i in range(len(vids) - 1):
                expected_transitions.add((vids[i], vids[i + 1]))

    expected_relationships = {
        "HAD_VISIT": len(visits_df),
        "ATTENDED_BY": len(visits_df),
        "DIAGNOSED_WITH": len(diagnoses_df),
        "PRESCRIBED": len(medications_df),
        "HAD_TEST": len(lab_tests_df),
        "FOLLOWED_BY": expected_followed_by,
    }

    return {
        "nodes": expected_nodes,
        "relationships": expected_relationships,
        "expected_transitions": expected_transitions,
        "patients_df": patients_df,
        "doctors_df": doctors_df,
        "visits_df": visits_df,
        "diagnoses_df": diagnoses_df,
        "medications_df": medications_df,
        "lab_tests_df": lab_tests_df,
    }


def verify_node_counts(session, expected_nodes: Dict[str, int]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """Compares database node counts against expected CSV counts."""
    query = """
    MATCH (n)
    RETURN head(labels(n)) AS label, count(*) AS count
    """
    records = session.run(query).data()
    actual_counts = {r["label"]: r["count"] for r in records if r["label"] is not None}

    comparison = {}
    errors = []

    for label, exp_cnt in expected_nodes.items():
        act_cnt = actual_counts.get(label, 0)
        diff = act_cnt - exp_cnt
        status = "PASS" if diff == 0 else "FAIL"
        if status == "FAIL":
            errors.append(f"Node count mismatch for :{label}: expected {exp_cnt}, found {act_cnt} in graph.")
        comparison[label] = {
            "expected": exp_cnt,
            "actual": act_cnt,
            "difference": diff,
            "status": status,
        }

    # Check for unexpected labels
    for label, act_cnt in actual_counts.items():
        if label not in expected_nodes:
            errors.append(f"Unexpected node label :{label} found with {act_cnt} nodes.")
            comparison[label] = {
                "expected": 0,
                "actual": act_cnt,
                "difference": act_cnt,
                "status": "FAIL",
            }

    return comparison, errors


def verify_relationship_counts(session, expected_relationships: Dict[str, int]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """Compares database relationship counts against expected CSV counts."""
    query = """
    MATCH ()-[r]->()
    RETURN type(r) AS rel_type, count(*) AS count
    """
    records = session.run(query).data()
    actual_counts = {r["rel_type"]: r["count"] for r in records}

    comparison = {}
    errors = []

    for rel_type, exp_cnt in expected_relationships.items():
        act_cnt = actual_counts.get(rel_type, 0)
        diff = act_cnt - exp_cnt
        status = "PASS" if diff == 0 else "FAIL"
        if status == "FAIL":
            errors.append(f"Relationship count mismatch for [:{rel_type}]: expected {exp_cnt}, found {act_cnt} in graph.")
        comparison[rel_type] = {
            "expected": exp_cnt,
            "actual": act_cnt,
            "difference": diff,
            "status": status,
        }

    # Check for unexpected relationship types
    for rel_type, act_cnt in actual_counts.items():
        if rel_type not in expected_relationships:
            errors.append(f"Unexpected relationship type [:{rel_type}] found with {act_cnt} edges.")
            comparison[rel_type] = {
                "expected": 0,
                "actual": act_cnt,
                "difference": act_cnt,
                "status": "FAIL",
            }

    return comparison, errors


def verify_core_entities(session, metrics: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Verifies property and link integrity of Patients, Doctors, and Visits."""
    errors = []

    # 1. Patient properties
    p_query = "MATCH (p:Patient) RETURN p.patient_id AS id, p.name AS name, toString(p.dob) AS dob, p.gender AS gender"
    p_records = {r["id"]: r for r in session.run(p_query).data()}
    for row in metrics["patients_df"].to_dict("records"):
        pid = row["patient_id"]
        if pid not in p_records:
            errors.append(f"Missing Patient node: {pid}")
        else:
            db_p = p_records[pid]
            for field in ["name", "dob", "gender"]:
                if str(db_p.get(field)) != str(row.get(field)):
                    errors.append(f"Patient {pid} property mismatch in '{field}': db='{db_p.get(field)}' vs csv='{row.get(field)}'")

    # 2. Doctor properties
    d_query = "MATCH (d:Doctor) RETURN d.doctor_id AS id, d.name AS name, d.specialty AS specialty"
    d_records = {r["id"]: r for r in session.run(d_query).data()}
    for row in metrics["doctors_df"].to_dict("records"):
        did = row["doctor_id"]
        if did not in d_records:
            errors.append(f"Missing Doctor node: {did}")
        else:
            db_d = d_records[did]
            for field in ["name", "specialty"]:
                if str(db_d.get(field)) != str(row.get(field)):
                    errors.append(f"Doctor {did} property mismatch in '{field}': db='{db_d.get(field)}' vs csv='{row.get(field)}'")

    # 3. Visit nodes and core links (:Patient)-[:HAD_VISIT]->(:Visit)-[:ATTENDED_BY]->(:Doctor)
    v_query = """
    MATCH (p:Patient)-[:HAD_VISIT]->(v:Visit)-[:ATTENDED_BY]->(d:Doctor)
    RETURN v.visit_id AS visit_id, toString(v.visit_date) AS visit_date, v.admission_type AS admission_type,
           p.patient_id AS patient_id, d.doctor_id AS doctor_id
    """
    v_records = {r["visit_id"]: r for r in session.run(v_query).data()}
    for row in metrics["visits_df"].to_dict("records"):
        vid = row["visit_id"]
        if vid not in v_records:
            errors.append(f"Missing or disconnected Visit path for: {vid}")
        else:
            db_v = v_records[vid]
            for field in ["visit_date", "admission_type", "patient_id", "doctor_id"]:
                if str(db_v.get(field)) != str(row.get(field)):
                    errors.append(f"Visit {vid} mismatch in '{field}': db='{db_v.get(field)}' vs csv='{row.get(field)}'")

    return len(errors) == 0, errors


def verify_clinical_entities(session, metrics: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Verifies property and link integrity of Diagnoses, Prescriptions, and Lab Tests."""
    errors = []

    # 1. Diagnoses and DIAGNOSED_WITH
    dx_query = """
    MATCH (v:Visit)-[r:DIAGNOSED_WITH]->(d:Diagnosis)
    RETURN v.visit_id AS visit_id, r.diagnosis_id AS diagnosis_id, r.status AS status, d.condition AS condition
    """
    dx_records = {r["visit_id"]: r for r in session.run(dx_query).data()}
    for row in metrics["diagnoses_df"].to_dict("records"):
        vid = row["visit_id"]
        if vid not in dx_records:
            errors.append(f"Missing DIAGNOSED_WITH relationship for visit: {vid}")
        else:
            db_dx = dx_records[vid]
            for field in ["diagnosis_id", "status", "condition"]:
                if str(db_dx.get(field)) != str(row.get(field)):
                    errors.append(f"Diagnosis on visit {vid} mismatch in '{field}': db='{db_dx.get(field)}' vs csv='{row.get(field)}'")

    # 2. Medications and PRESCRIBED
    rx_query = """
    MATCH (v:Visit)-[r:PRESCRIBED]->(m:Medication)
    RETURN v.visit_id AS visit_id, r.prescription_id AS prescription_id, r.dosage AS dosage,
           r.is_effective AS is_effective, m.name AS medication_name
    """
    rx_records = {r["visit_id"]: r for r in session.run(rx_query).data()}
    for row in metrics["medications_df"].to_dict("records"):
        vid = row["visit_id"]
        if vid not in rx_records:
            errors.append(f"Missing PRESCRIBED relationship for visit: {vid}")
        else:
            db_rx = rx_records[vid]
            for field in ["prescription_id", "dosage", "is_effective", "medication_name"]:
                if str(db_rx.get(field)).lower() != str(row.get(field)).lower():
                    errors.append(f"Prescription on visit {vid} mismatch in '{field}': db='{db_rx.get(field)}' vs csv='{row.get(field)}'")

    # 3. Lab Tests and HAD_TEST
    lab_query = """
    MATCH (v:Visit)-[:HAD_TEST]->(t:LabTest)
    RETURN v.visit_id AS visit_id, t.test_id AS test_id, t.test_name AS test_name,
           t.value AS value, t.unit AS unit
    """
    lab_records = {r["visit_id"]: r for r in session.run(lab_query).data()}
    for row in metrics["lab_tests_df"].to_dict("records"):
        vid = row["visit_id"]
        if vid not in lab_records:
            errors.append(f"Missing HAD_TEST relationship for visit: {vid}")
        else:
            db_lab = lab_records[vid]
            for field in ["test_id", "test_name", "unit"]:
                if str(db_lab.get(field)) != str(row.get(field)):
                    errors.append(f"Lab test on visit {vid} mismatch in '{field}': db='{db_lab.get(field)}' vs csv='{row.get(field)}'")
            # Float numeric value check
            if abs(float(db_lab.get("value", 0)) - float(row.get("value", 0))) > 1e-4:
                errors.append(f"Lab test on visit {vid} mismatch in 'value': db={db_lab.get('value')} vs csv={row.get('value')}")

    return len(errors) == 0, errors


def verify_trajectories(session, expected_transitions: set) -> Tuple[bool, List[str]]:
    """Verifies FOLLOWED_BY edges connect sequential visits for the same patient in chronological order."""
    query = """
    MATCH (v1:Visit)-[:FOLLOWED_BY]->(v2:Visit)
    MATCH (p1:Patient)-[:HAD_VISIT]->(v1)
    MATCH (p2:Patient)-[:HAD_VISIT]->(v2)
    RETURN v1.visit_id AS v1, v2.visit_id AS v2,
           p1.patient_id AS p1, p2.patient_id AS p2,
           toString(v1.visit_date) AS d1, toString(v2.visit_date) AS d2
    """
    records = session.run(query).data()
    errors = []

    actual_transitions = set()
    for r in records:
        v1, v2 = r["v1"], r["v2"]
        actual_transitions.add((v1, v2))

        # Check cross-patient transition
        if r["p1"] != r["p2"]:
            errors.append(f"Cross-patient FOLLOWED_BY edge detected between {v1} (Patient {r['p1']}) and {v2} (Patient {r['p2']}).")

        # Check chronological order (d1 <= d2)
        if r["d1"] > r["d2"]:
            errors.append(f"Non-chronological FOLLOWED_BY edge: {v1} on {r['d1']} followed by {v2} on {r['d2']}.")

    missing = expected_transitions - actual_transitions
    if missing:
        errors.append(f"Missing {len(missing)} expected FOLLOWED_BY trajectory edge(s): {sorted(list(missing))[:3]}")

    unexpected = actual_transitions - expected_transitions
    if unexpected:
        errors.append(f"Unexpected {len(unexpected)} FOLLOWED_BY edge(s) found in graph: {sorted(list(unexpected))[:3]}")

    return len(errors) == 0, errors


def verify_constraints(session) -> Tuple[Dict[str, Any], List[str]]:
    """Inspects existing database constraints and indexes, checking for schema mismatches."""
    warnings = []
    constraints = session.run("SHOW CONSTRAINTS").data()

    diagnosis_constraint_on_id = False
    diagnosis_constraint_on_condition = False

    for c in constraints:
        labels = c.get("labelsOrTypes", [])
        props = c.get("properties", [])
        if "Diagnosis" in labels:
            if "diagnosis_id" in props:
                diagnosis_constraint_on_id = True
            if "condition" in props:
                diagnosis_constraint_on_condition = True

    if diagnosis_constraint_on_id and not diagnosis_constraint_on_condition:
        warnings.append(
            "Schema Mismatch Identified: Constraint 'unique_diagnosis_id' enforces uniqueness on Diagnosis.diagnosis_id, "
            "but Diagnosis nodes are merged on 'condition' and lack a 'diagnosis_id' property (diagnosis_id resides on [:DIAGNOSED_WITH])."
        )

    return {"constraints": constraints, "mismatch_detected": diagnosis_constraint_on_id}, warnings


def verify_live_graph(driver=None, data_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Executes a comprehensive, read-only graph verification comparing
    AuraDB against source CSV datasets.
    """
    close_driver = False
    if driver is None:
        try:
            driver = get_driver()
            close_driver = True
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to initialize Neo4j driver: {e}",
                "status": "FAIL"
            }

    all_errors = []
    all_warnings = []

    try:
        driver.verify_connectivity()
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to connect to Neo4j database: {e}",
            "status": "FAIL"
        }

    try:
        metrics = derive_expected_metrics(data_dir)

        with driver.session(default_access_mode="READ") as session:
            # 1. Node Counts
            node_comp, n_errs = verify_node_counts(session, metrics["nodes"])
            all_errors.extend(n_errs)

            # 2. Relationship Counts
            rel_comp, r_errs = verify_relationship_counts(session, metrics["relationships"])
            all_errors.extend(r_errs)

            # 3. Core Entities
            _, core_errs = verify_core_entities(session, metrics)
            all_errors.extend(core_errs)

            # 4. Clinical Entities
            _, clin_errs = verify_clinical_entities(session, metrics)
            all_errors.extend(clin_errs)

            # 5. Chronological Trajectories
            _, traj_errs = verify_trajectories(session, metrics["expected_transitions"])
            all_errors.extend(traj_errs)

            # 6. Constraints & Indexes
            schema_info, schema_warns = verify_constraints(session)
            all_warnings.extend(schema_warns)

        is_valid = len(all_errors) == 0

        report = {
            "success": True,
            "is_valid": is_valid,
            "node_comparison": node_comp,
            "relationship_comparison": rel_comp,
            "errors": all_errors,
            "warnings": all_warnings,
            "schema_info": schema_info,
            "status": "PASS" if is_valid else "FAIL",
        }

        print_verification_report(report)
        return report

    finally:
        if close_driver and driver:
            driver.close()


def print_verification_report(report: Dict[str, Any]) -> None:
    """Formats and prints the verification report."""
    print("\n" + "=" * 90)
    print("                 NEO4J LIVE GRAPH VERIFICATION REPORT")
    print("=" * 90)

    if not report.get("success"):
        print(f"DATABASE CONNECTION / VERIFICATION ERROR: {report.get('error')}")
        print("=" * 90)
        return

    print("--- 1. NODE COUNTS ---")
    print(f"{'Label':<18} | {'Expected':<10} | {'Actual':<10} | {'Diff':<8} | {'Status':<6}")
    print("-" * 60)
    for label, d in report["node_comparison"].items():
        print(f":{label:<17} | {d['expected']:<10} | {d['actual']:<10} | {d['difference']:<8} | {d['status']:<6}")

    print("\n--- 2. RELATIONSHIP COUNTS ---")
    print(f"{'Relationship':<18} | {'Expected':<10} | {'Actual':<10} | {'Diff':<8} | {'Status':<6}")
    print("-" * 60)
    for rel_type, d in report["relationship_comparison"].items():
        print(f"[:{rel_type:<16}] | {d['expected']:<10} | {d['actual']:<10} | {d['difference']:<8} | {d['status']:<6}")

    print("\n" + "=" * 90)
    status_str = report["status"]
    print(f"OVERALL VERIFICATION STATUS: {status_str} | Errors: {len(report['errors'])}, Warnings: {len(report['warnings'])}")
    print("=" * 90)

    if report["errors"]:
        print("\n[CRITICAL GRAPH INCONSISTENCIES]")
        for err in report["errors"]:
            print(f"  ✗ {err}")

    if report["warnings"]:
        print("\n[ARCHITECTURAL WARNINGS & OBSERVATIONS]")
        for w in report["warnings"]:
            print(f"  ⚠ {w}")
    print()


if __name__ == "__main__":
    rep = verify_live_graph()
    if not rep.get("success") or not rep.get("is_valid"):
        sys.exit(1)
    sys.exit(0)
