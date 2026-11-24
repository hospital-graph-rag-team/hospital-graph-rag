from datetime import date, datetime
from typing import Dict, List, Any, Optional
import neo4j

try:
    from graph.connection import get_driver
except ModuleNotFoundError:
    from connection import get_driver


# =====================================================================
# 1. JSON Serialization Helper
# =====================================================================

def serialize_neo4j_value(val: Any) -> Any:
    """
    Recursively converts Neo4j results, temporal types, and Python date/time
    objects into JSON-serializable Python primitives while strictly preserving
    numeric (int, float), boolean (True, False), and null types.
    """
    if val is None:
        return None

    # Handle Python standard date/datetime
    if isinstance(val, (date, datetime)):
        return val.isoformat()

    # Handle Neo4j temporal types (Date, DateTime, Time, Duration)
    mod = getattr(type(val), "__module__", "")
    if "neo4j" in mod or hasattr(val, "iso_format"):
        return str(val)

    # Handle nested dictionaries
    if isinstance(val, dict):
        return {k: serialize_neo4j_value(v) for k, v in val.items()}

    # Handle collections (list, tuple, set)
    if isinstance(val, (list, tuple, set)):
        return [serialize_neo4j_value(item) for item in val]

    # Handle primitives (float, int, bool, str)
    if isinstance(val, (int, float, bool, str)):
        return val

    # Fallback to string representation for unsupported types
    return str(val)


# =====================================================================
# 2. Backward-Compatible Retrieval Functions (Person 1 APIs)
# =====================================================================

def get_patient_history(patient_id: str, driver: Optional[Any] = None) -> List[Dict[str, Any]]:
    """
    Retrieves full longitudinal history for a given patient.
    Preserves exact Person 1 signature, Cypher query, and return format.
    """
    query = """
    MATCH (p:Patient {patient_id: $patient_id})-[:HAD_VISIT]->(v:Visit)
    OPTIONAL MATCH (v)-[:DIAGNOSED_WITH]->(d:Diagnosis)
    OPTIONAL MATCH (v)-[:PRESCRIBED]->(m:Medication)
    OPTIONAL MATCH (v)-[:HAD_TEST]->(t:LabTest)
    OPTIONAL MATCH (v)-[:ATTENDED_BY]->(doc:Doctor)
    RETURN v.visit_id AS visit_id,
           v.visit_date AS visit_date,
           v.admission_type AS admission_type,
           doc.name AS doctor,
           d.condition AS diagnosis,
           m.name AS prescribed_medication,
           t.test_name AS lab_test,
           t.value AS lab_value,
           t.unit AS lab_unit
    ORDER BY v.visit_date ASC
    """
    should_close = False
    if driver is None:
        driver = get_driver()
        should_close = True

    try:
        with driver.session(default_access_mode="READ") as session:
            result = session.run(query, patient_id=patient_id)
            return [record.data() for record in result]
    finally:
        if should_close and driver:
            driver.close()


def get_best_medications_for_condition(condition: str, driver: Optional[Any] = None) -> List[Dict[str, Any]]:
    """
    Retrieves comparative medication efficacy rates for a specific condition.
    Preserves exact Person 1 signature, Cypher query, and return format.
    """
    query = """
    MATCH (v1:Visit)-[:FOLLOWED_BY]->(v2:Visit)
    MATCH (v1)-[:DIAGNOSED_WITH]->(d:Diagnosis {condition: $condition})
    MATCH (v1)-[:PRESCRIBED]->(m:Medication)
    MATCH (v1)-[:HAD_TEST]->(t1:LabTest)
    MATCH (v2)-[:HAD_TEST]->(t2:LabTest)
    WHERE t1.test_name = t2.test_name
    WITH m.name AS medication,
          t1.test_name AS biomarker,
          count(*) AS total_cases,
          sum(CASE WHEN t2.value < t1.value THEN 1 ELSE 0 END) AS improved_cases
    RETURN medication,
           biomarker,
           total_cases,
           improved_cases,
           round(toFloat(improved_cases) / total_cases * 100, 2) AS betterment_rate_pct
    ORDER BY betterment_rate_pct DESC
    """
    should_close = False
    if driver is None:
        driver = get_driver()
        should_close = True

    try:
        with driver.session(default_access_mode="READ") as session:
            result = session.run(query, condition=condition)
            return [record.data() for record in result]
    finally:
        if should_close and driver:
            driver.close()


# =====================================================================
# 3. Advanced Graph Retrieval Functions (Person 2 Phase 4 APIs)
# =====================================================================

def get_patient_directory(driver: Optional[Any] = None) -> List[Dict[str, Any]]:
    """
    Retrieves the complete directory of patients in deterministic order.
    Used for UI patient selection and cohort indexing.
    """
    query = """
    MATCH (p:Patient)
    RETURN p.patient_id AS patient_id,
           p.name AS name,
           toString(p.dob) AS dob,
           p.gender AS gender
    ORDER BY p.patient_id ASC
    """
    should_close = False
    if driver is None:
        driver = get_driver()
        should_close = True

    try:
        with driver.session(default_access_mode="READ") as session:
            records = session.run(query).data()
            return serialize_neo4j_value(records)
    finally:
        if should_close and driver:
            driver.close()


def get_patient_profile(patient_id: str, driver: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves demographic and encounter summary metadata for a patient.
    Returns None if patient is not found.
    """
    query = """
    MATCH (p:Patient {patient_id: $patient_id})
    OPTIONAL MATCH (p)-[:HAD_VISIT]->(v:Visit)
    WITH p, count(v) AS visit_count, min(v.visit_date) AS first_visit_date, max(v.visit_date) AS latest_visit_date
    RETURN p.patient_id AS patient_id,
           p.name AS name,
           toString(p.dob) AS dob,
           p.gender AS gender,
           visit_count,
           toString(first_visit_date) AS first_visit_date,
           toString(latest_visit_date) AS latest_visit_date
    """
    should_close = False
    if driver is None:
        driver = get_driver()
        should_close = True

    try:
        with driver.session(default_access_mode="READ") as session:
            record = session.run(query, patient_id=patient_id).single()
            if not record:
                return None
            return serialize_neo4j_value(record.data())
    finally:
        if should_close and driver:
            driver.close()


def get_patient_timeline(patient_id: str, driver: Optional[Any] = None) -> List[Dict[str, Any]]:
    """
    Retrieves a structured, chronological timeline of all visits for a patient.
    Uses Cypher pattern comprehension to prevent Cartesian multiplication of clinical records.
    """
    query = """
    MATCH (p:Patient {patient_id: $patient_id})-[:HAD_VISIT]->(v:Visit)
    OPTIONAL MATCH (v)-[:ATTENDED_BY]->(doc:Doctor)
    WITH v, doc ORDER BY v.visit_date ASC, v.visit_id ASC
    RETURN v.visit_id AS visit_id,
           toString(v.visit_date) AS visit_date,
           v.admission_type AS admission_type,
           CASE WHEN doc IS NOT NULL THEN {
               doctor_id: doc.doctor_id,
               name: doc.name,
               specialty: doc.specialty
           } ELSE null END AS doctor,
           [(v)-[r_dx:DIAGNOSED_WITH]->(d:Diagnosis) | {
               diagnosis_id: r_dx.diagnosis_id,
               condition: d.condition,
               status: r_dx.status
           }] AS diagnoses,
           [(v)-[r_rx:PRESCRIBED]->(m:Medication) | {
               prescription_id: r_rx.prescription_id,
               medication_name: m.name,
               dosage: r_rx.dosage,
               is_effective: r_rx.is_effective
           }] AS medications,
           [(v)-[:HAD_TEST]->(t:LabTest) | {
               test_id: t.test_id,
               test_name: t.test_name,
               value: t.value,
               unit: t.unit
           }] AS lab_tests
    ORDER BY v.visit_date ASC, v.visit_id ASC
    """
    should_close = False
    if driver is None:
        driver = get_driver()
        should_close = True

    try:
        with driver.session(default_access_mode="READ") as session:
            records = session.run(query, patient_id=patient_id).data()
            return serialize_neo4j_value(records)
    finally:
        if should_close and driver:
            driver.close()


def get_lab_trends(
    patient_id: str,
    test_name: Optional[str] = None,
    driver: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    Retrieves chronological laboratory readings for a patient grouped by biomarker and unit.
    Calculates initial value, latest value, absolute change, percentage change, and trend direction.
    """
    query = """
    MATCH (p:Patient {patient_id: $patient_id})-[:HAD_VISIT]->(v:Visit)-[:HAD_TEST]->(t:LabTest)
    WHERE $test_name IS NULL OR t.test_name = $test_name
    RETURN v.visit_id AS visit_id,
           toString(v.visit_date) AS visit_date,
           t.test_id AS test_id,
           t.test_name AS test_name,
           t.value AS value,
           t.unit AS unit
    ORDER BY t.test_name ASC, t.unit ASC, v.visit_date ASC, v.visit_id ASC
    """
    should_close = False
    if driver is None:
        driver = get_driver()
        should_close = True

    try:
        with driver.session(default_access_mode="READ") as session:
            records = session.run(query, patient_id=patient_id, test_name=test_name).data()

            # Group observations by (test_name, unit)
            groups: Dict[tuple, List[Dict[str, Any]]] = {}
            for r in records:
                key = (r["test_name"], r["unit"])
                if key not in groups:
                    groups[key] = []
                groups[key].append({
                    "visit_id": r["visit_id"],
                    "visit_date": str(r["visit_date"]),
                    "test_id": r["test_id"],
                    "value": float(r["value"]),
                    "unit": r["unit"],
                })

            trends = []
            for (biomarker, unit), obs in sorted(groups.items()):
                init_val = obs[0]["value"]
                latest_val = obs[-1]["value"]
                abs_change = round(latest_val - init_val, 4)

                pct_change = None
                if init_val != 0:
                    pct_change = round((abs_change / init_val) * 100, 2)

                if len(obs) < 2:
                    direction = "insufficient_data"
                    abs_change = 0.0
                    pct_change = None
                else:
                    if abs(abs_change) < 1e-6:
                        direction = "unchanged"
                    elif latest_val > init_val:
                        direction = "increased"
                    else:
                        direction = "decreased"

                trends.append({
                    "patient_id": patient_id,
                    "biomarker": biomarker,
                    "unit": unit,
                    "observation_count": len(obs),
                    "initial_value": init_val,
                    "latest_value": latest_val,
                    "absolute_change": abs_change,
                    "percentage_change": pct_change,
                    "direction": direction,
                    "observations": obs,
                })

            return serialize_neo4j_value(trends)
    finally:
        if should_close and driver:
            driver.close()


def get_followup_comparison(patient_id: str, driver: Optional[Any] = None) -> List[Dict[str, Any]]:
    """
    Compares sequential patient encounters connected via [:FOLLOWED_BY] transitions.
    Calculates elapsed days and delta changes for matching biomarkers.
    """
    query = """
    MATCH (p:Patient {patient_id: $patient_id})-[:HAD_VISIT]->(v1:Visit)-[:FOLLOWED_BY]->(v2:Visit)
    MATCH (p)-[:HAD_VISIT]->(v2)
    OPTIONAL MATCH (v1)-[:ATTENDED_BY]->(d1:Doctor)
    OPTIONAL MATCH (v2)-[:ATTENDED_BY]->(d2:Doctor)
    WITH v1, v2, d1, d2 ORDER BY v1.visit_date ASC, v1.visit_id ASC
    RETURN v1.visit_id AS v1_id, toString(v1.visit_date) AS v1_date, v1.admission_type AS v1_admission,
           d1.name AS v1_doctor,
           v2.visit_id AS v2_id, toString(v2.visit_date) AS v2_date, v2.admission_type AS v2_admission,
           d2.name AS v2_doctor,
           [(v1)-[r:DIAGNOSED_WITH]->(d:Diagnosis) | {diagnosis_id: r.diagnosis_id, condition: d.condition, status: r.status}] AS v1_diagnoses,
           [(v2)-[r:DIAGNOSED_WITH]->(d:Diagnosis) | {diagnosis_id: r.diagnosis_id, condition: d.condition, status: r.status}] AS v2_diagnoses,
           [(v1)-[r:PRESCRIBED]->(m:Medication) | {prescription_id: r.prescription_id, medication_name: m.name, dosage: r.dosage, is_effective: r.is_effective}] AS v1_prescriptions,
           [(v2)-[r:PRESCRIBED]->(m:Medication) | {prescription_id: r.prescription_id, medication_name: m.name, dosage: r.dosage, is_effective: r.is_effective}] AS v2_prescriptions,
           [(v1)-[:HAD_TEST]->(t1:LabTest) | {test_id: t1.test_id, test_name: t1.test_name, value: t1.value, unit: t1.unit}] AS v1_labs,
           [(v2)-[:HAD_TEST]->(t2:LabTest) | {test_id: t2.test_id, test_name: t2.test_name, value: t2.value, unit: t2.unit}] AS v2_labs
    ORDER BY v1.visit_date ASC, v1.visit_id ASC
    """
    should_close = False
    if driver is None:
        driver = get_driver()
        should_close = True

    try:
        with driver.session(default_access_mode="READ") as session:
            records = session.run(query, patient_id=patient_id).data()
            comparisons = []

            for r in records:
                v1_dt = datetime.fromisoformat(str(r["v1_date"]))
                v2_dt = datetime.fromisoformat(str(r["v2_date"]))
                days_between = (v2_dt - v1_dt).days

                # Match comparable laboratory tests by name and unit
                v1_lab_map = {(t["test_name"], t["unit"]): t for t in r.get("v1_labs", [])}
                v2_lab_map = {(t["test_name"], t["unit"]): t for t in r.get("v2_labs", [])}

                lab_comparisons = []
                for (bmark, unit), t1 in v1_lab_map.items():
                    if (bmark, unit) in v2_lab_map:
                        t2 = v2_lab_map[(bmark, unit)]
                        val1 = float(t1["value"])
                        val2 = float(t2["value"])
                        abs_chg = round(val2 - val1, 4)
                        pct_chg = None
                        if val1 != 0:
                            pct_chg = round((abs_chg / val1) * 100, 2)

                        if abs(abs_chg) < 1e-6:
                            direction = "unchanged"
                        elif val2 > val1:
                            direction = "increased"
                        else:
                            direction = "decreased"

                        lab_comparisons.append({
                            "biomarker": bmark,
                            "unit": unit,
                            "v1_test_id": t1["test_id"],
                            "v1_value": val1,
                            "v2_test_id": t2["test_id"],
                            "v2_value": val2,
                            "absolute_change": abs_chg,
                            "percentage_change": pct_chg,
                            "direction": direction,
                        })

                comparisons.append({
                    "patient_id": patient_id,
                    "previous_visit": {
                        "visit_id": r["v1_id"],
                        "visit_date": str(r["v1_date"]),
                        "admission_type": r["v1_admission"],
                        "doctor": r["v1_doctor"],
                        "diagnoses": r["v1_diagnoses"],
                        "prescriptions": r["v1_prescriptions"],
                    },
                    "followup_visit": {
                        "visit_id": r["v2_id"],
                        "visit_date": str(r["v2_date"]),
                        "admission_type": r["v2_admission"],
                        "doctor": r["v2_doctor"],
                        "diagnoses": r["v2_diagnoses"],
                        "prescriptions": r["v2_prescriptions"],
                    },
                    "days_between": days_between,
                    "lab_comparisons": lab_comparisons,
                })

            return serialize_neo4j_value(comparisons)
    finally:
        if should_close and driver:
            driver.close()


def get_medication_outcomes(condition: str, driver: Optional[Any] = None) -> Dict[str, Any]:
    """
    Computes rigorous synthetic observational medication outcomes for consecutive visit transitions.
    Requires matching condition presence at both visits and comparable laboratory biomarkers.
    Reports unique patient counts, transition counts, improved/worsened/unchanged statistics,
    and supporting evidence identifiers.
    """
    query = """
    MATCH (p:Patient)-[:HAD_VISIT]->(v1:Visit)-[:FOLLOWED_BY]->(v2:Visit)
    MATCH (p)-[:HAD_VISIT]->(v2)
    MATCH (v1)-[r_dx1:DIAGNOSED_WITH]->(d1:Diagnosis {condition: $condition})
    MATCH (v2)-[r_dx2:DIAGNOSED_WITH]->(d2:Diagnosis {condition: $condition})
    MATCH (v1)-[r_rx:PRESCRIBED]->(m:Medication)
    MATCH (v1)-[:HAD_TEST]->(t1:LabTest)
    MATCH (v2)-[:HAD_TEST]->(t2:LabTest)
    WHERE t1.test_name = t2.test_name AND t1.unit = t2.unit
    RETURN p.patient_id AS patient_id,
           m.name AS medication_name,
           r_rx.prescription_id AS prescription_id,
           r_rx.dosage AS dosage,
           r_rx.is_effective AS generator_is_effective,
           v1.visit_id AS v1_id, toString(v1.visit_date) AS v1_date,
           v2.visit_id AS v2_id, toString(v2.visit_date) AS v2_date,
           t1.test_id AS t1_id, t1.test_name AS biomarker, t1.value AS v1_value, t1.unit AS unit,
           t2.test_id AS t2_id, t2.value AS v2_value
    ORDER BY medication_name ASC, v1.visit_date ASC, v1.visit_id ASC
    """
    should_close = False
    if driver is None:
        driver = get_driver()
        should_close = True

    try:
        with driver.session(default_access_mode="READ") as session:
            records = session.run(query, condition=condition).data()

            med_groups: Dict[str, Dict[str, Any]] = {}
            all_patients = set()
            total_transitions = len(records)
            primary_biomarker = None
            primary_unit = None

            for r in records:
                m_name = r["medication_name"]
                all_patients.add(r["patient_id"])
                if primary_biomarker is None:
                    primary_biomarker = r["biomarker"]
                    primary_unit = r["unit"]

                if m_name not in med_groups:
                    med_groups[m_name] = {
                        "medication": m_name,
                        "biomarker": r["biomarker"],
                        "unit": r["unit"],
                        "unique_patients": set(),
                        "eligible_transitions": 0,
                        "improved_transitions": 0,
                        "worsened_transitions": 0,
                        "unchanged_transitions": 0,
                        "evidence": [],
                    }

                group = med_groups[m_name]
                group["eligible_transitions"] += 1
                group["unique_patients"].add(r["patient_id"])

                v1_val = float(r["v1_value"])
                v2_val = float(r["v2_value"])
                diff = round(v2_val - v1_val, 4)

                # For the three synthetic chronic conditions (Diabetes, Hypertension, Hyperlipidemia),
                # lower biomarker readings (HbA1c, Systolic BP, LDL Cholesterol) reflect therapeutic improvement.
                if abs(diff) < 1e-6:
                    group["unchanged_transitions"] += 1
                    direction = "unchanged"
                elif v2_val < v1_val:
                    group["improved_transitions"] += 1
                    direction = "improved"
                else:
                    group["worsened_transitions"] += 1
                    direction = "worsened"

                group["evidence"].append({
                    "patient_id": r["patient_id"],
                    "v1_id": r["v1_id"],
                    "v2_id": r["v2_id"],
                    "v1_value": v1_val,
                    "v2_value": v2_val,
                    "delta": diff,
                    "direction": direction,
                    "prescription_id": r["prescription_id"],
                })

            medications_out = []
            for m_name, g in sorted(med_groups.items()):
                tot = g["eligible_transitions"]
                improved = g["improved_transitions"]
                betterment_pct = round((improved / tot) * 100, 2) if tot > 0 else 0.0

                medications_out.append({
                    "medication": m_name,
                    "biomarker": g["biomarker"],
                    "unit": g["unit"],
                    "unique_patient_count": len(g["unique_patients"]),
                    "eligible_transitions": tot,
                    "improved_transitions": improved,
                    "worsened_transitions": g["worsened_transitions"],
                    "unchanged_transitions": g["unchanged_transitions"],
                    "betterment_rate_pct": betterment_pct,
                    "evidence_sample": g["evidence"][:3],
                })

            # Sort by betterment_rate_pct descending, then medication name ASC
            medications_out.sort(key=lambda x: (-x["betterment_rate_pct"], x["medication"]))

            result = {
                "condition": condition,
                "biomarker": primary_biomarker,
                "unit": primary_unit,
                "total_eligible_transitions": total_transitions,
                "total_unique_patients": len(all_patients),
                "medications": medications_out,
                "disclaimer": (
                    "Synthetic observational outcomes based on consecutive visit transitions where biomarker values decreased. "
                    "Does not establish medical causality, clinical efficacy, or individual treatment recommendations."
                ),
            }

            return serialize_neo4j_value(result)
    finally:
        if should_close and driver:
            driver.close()
