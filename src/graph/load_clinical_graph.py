import pandas as pd
from pathlib import Path
from connection import get_driver

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

# Uniqueness constraints for clinical entities
CONSTRAINTS = [
    "CREATE CONSTRAINT unique_diagnosis_id IF NOT EXISTS FOR (d:Diagnosis) REQUIRE d.diagnosis_id IS UNIQUE",
    "CREATE CONSTRAINT unique_medication_name IF NOT EXISTS FOR (m:Medication) REQUIRE m.name IS UNIQUE",
    "CREATE CONSTRAINT unique_test_id IF NOT EXISTS FOR (t:LabTest) REQUIRE t.test_id IS UNIQUE"
]

LOAD_DIAGNOSES_QUERY = """
UNWIND $rows AS row
MERGE (d:Diagnosis {condition: row.condition})
WITH d, row
MATCH (v:Visit {visit_id: row.visit_id})
MERGE (v)-[:DIAGNOSED_WITH {diagnosis_id: row.diagnosis_id, status: row.status}]->(d)
"""

LOAD_MEDICATIONS_QUERY = """
UNWIND $rows AS row
MERGE (m:Medication {name: row.medication_name})
WITH m, row
MATCH (v:Visit {visit_id: row.visit_id})
MERGE (v)-[:PRESCRIBED {
    prescription_id: row.prescription_id,
    dosage: row.dosage,
    is_effective: row.is_effective
}]->(m)
"""

LOAD_LAB_TESTS_QUERY = """
UNWIND $rows AS row
MERGE (t:LabTest {test_id: row.test_id})
ON CREATE SET 
    t.test_name = row.test_name,
    t.value = toFloat(row.value),
    t.unit = row.unit
WITH t, row
MATCH (v:Visit {visit_id: row.visit_id})
MERGE (v)-[:HAD_TEST]->(t)
"""

def setup_constraints(session):
    print("Setting up clinical uniqueness constraints...")
    for constraint in CONSTRAINTS:
        session.run(constraint)
    print("✓ Clinical constraints active.")

def import_clinical_data():
    diagnoses_df = pd.read_csv(DATA_DIR / "diagnoses.csv")
    medications_df = pd.read_csv(DATA_DIR / "medications.csv")
    lab_tests_df = pd.read_csv(DATA_DIR / "lab_tests.csv")

    driver = get_driver()
    try:
        with driver.session() as session:
            # 1. Setup constraints
            setup_constraints(session)

            # 2. Ingest Diagnoses & link to Visits
            print(f"Linking {len(diagnoses_df)} Diagnoses to Visits...")
            session.run(LOAD_DIAGNOSES_QUERY, rows=diagnoses_df.to_dict(orient="records"))

            # 3. Ingest Medications & link to Visits
            print(f"Linking {len(medications_df)} Prescriptions to Visits...")
            session.run(LOAD_MEDICATIONS_QUERY, rows=medications_df.to_dict(orient="records"))

            # 4. Ingest Lab Tests & link to Visits
            print(f"Linking {len(lab_tests_df)} Lab Tests to Visits...")
            session.run(LOAD_LAB_TESTS_QUERY, rows=lab_tests_df.to_dict(orient="records"))

            print("✓ Successfully ingested clinical entities into Neo4j Aura.")
    finally:
        driver.close()

if __name__ == "__main__":
    import_clinical_data()