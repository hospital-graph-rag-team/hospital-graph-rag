import pandas as pd
from pathlib import Path
from connection import get_driver

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

# Constraints guarantee uniqueness and speed up lookup/match queries
CONSTRAINTS = [
    "CREATE CONSTRAINT unique_patient_id IF NOT EXISTS FOR (p:Patient) REQUIRE p.patient_id IS UNIQUE",
    "CREATE CONSTRAINT unique_doctor_id IF NOT EXISTS FOR (d:Doctor) REQUIRE d.doctor_id IS UNIQUE",
    "CREATE CONSTRAINT unique_visit_id IF NOT EXISTS FOR (v:Visit) REQUIRE v.visit_id IS UNIQUE"
]

LOAD_PATIENTS_QUERY = """
UNWIND $rows AS row
MERGE (p:Patient {patient_id: row.patient_id})
ON CREATE SET 
    p.name = row.name,
    p.dob = date(row.dob),
    p.gender = row.gender
"""

LOAD_DOCTORS_QUERY = """
UNWIND $rows AS row
MERGE (d:Doctor {doctor_id: row.doctor_id})
ON CREATE SET 
    d.name = row.name,
    d.specialty = row.specialty
"""

LOAD_VISITS_QUERY = """
UNWIND $rows AS row
MERGE (v:Visit {visit_id: row.visit_id})
ON CREATE SET 
    v.visit_date = date(row.visit_date),
    v.admission_type = row.admission_type
WITH v, row
MATCH (p:Patient {patient_id: row.patient_id})
MERGE (p)-[:HAD_VISIT]->(v)
WITH v, row
MATCH (d:Doctor {doctor_id: row.doctor_id})
MERGE (v)-[:ATTENDED_BY]->(d)
"""

# Temporal chaining: links consecutive visits per patient chronologically
BUILD_VISIT_CHAIN_QUERY = """
MATCH (p:Patient)-[:HAD_VISIT]->(v:Visit)
WITH p, v ORDER BY v.visit_date ASC, v.visit_id ASC
WITH p, collect(v) AS visits
WHERE size(visits) > 1
UNWIND range(0, size(visits) - 2) AS idx
WITH visits[idx] AS vCurrent, visits[idx + 1] AS vNext
MERGE (vCurrent)-[:FOLLOWED_BY]->(vNext)
"""

def setup_constraints(session):
    print("Setting up unique constraints...")
    for constraint in CONSTRAINTS:
        session.run(constraint)
    print("✓ Constraints active.")

def import_core_data():
    patients_df = pd.read_csv(DATA_DIR / "patients.csv")
    doctors_df = pd.read_csv(DATA_DIR / "doctors.csv")
    visits_df = pd.read_csv(DATA_DIR / "visits.csv")

    driver = get_driver()
    try:
        with driver.session() as session:
            # 1. Setup constraints
            setup_constraints(session)

            # 2. Ingest Patients
            print(f"Importing {len(patients_df)} Patients...")
            session.run(LOAD_PATIENTS_QUERY, rows=patients_df.to_dict(orient="records"))

            # 3. Ingest Doctors
            print(f"Importing {len(doctors_df)} Doctors...")
            session.run(LOAD_DOCTORS_QUERY, rows=doctors_df.to_dict(orient="records"))

            # 4. Ingest Visits + base relationships
            print(f"Importing {len(visits_df)} Visits and establishing base graph links...")
            session.run(LOAD_VISITS_QUERY, rows=visits_df.to_dict(orient="records"))

            # 5. Build chronological trajectories
            print("Building temporal [:FOLLOWED_BY] visit trajectories...")
            session.run(BUILD_VISIT_CHAIN_QUERY)

            print("✓ Core knowledge graph and visit chains successfully loaded into Neo4j Aura.")
    finally:
        driver.close()

if __name__ == "__main__":
    import_core_data()