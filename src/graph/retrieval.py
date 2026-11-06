try:
    from graph.connection import get_driver
except ModuleNotFoundError:
    from connection import get_driver

def get_patient_history(patient_id: str):
    """Retrieves full longitudinal history for a given patient."""
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
    driver = get_driver()
    try:
        with driver.session() as session:
            result = session.run(query, patient_id=patient_id)
            return [record.data() for record in result]
    finally:
        driver.close()

def get_best_medications_for_condition(condition: str):
    """Retrieves comparative medication efficacy rates for a specific condition."""
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
    driver = get_driver()
    try:
        with driver.session() as session:
            result = session.run(query, condition=condition)
            return [record.data() for record in result]
    finally:
        driver.close()

if __name__ == "__main__":
    print("--- Testing Patient Retrieval (P101) ---")
    p_history = get_patient_history("P101")
    for step in p_history:
        print(f"[{step['visit_date']}] {step['admission_type']} | Dx: {step['diagnosis']} | Rx: {step['prescribed_medication']} | Lab: {step['lab_test']} = {step['lab_value']} {step['lab_unit']}")

    print("\n--- Testing Drug Efficacy Retrieval (Type 2 Diabetes) ---")
    med_stats = get_best_medications_for_condition("Type 2 Diabetes")
    for stat in med_stats:
        print(f"Medication: {stat['medication']} | Betterment: {stat['betterment_rate_pct']}% ({stat['improved_cases']}/{stat['total_cases']} patients)")