try:
    from graph.connection import get_driver
except ModuleNotFoundError:
    from connection import get_driver

BETTERMENT_RATE_QUERY = """
MATCH (v1:Visit)-[:FOLLOWED_BY]->(v2:Visit)
MATCH (v1)-[:DIAGNOSED_WITH]->(d:Diagnosis)
MATCH (v1)-[:PRESCRIBED]->(m:Medication)
MATCH (v1)-[:HAD_TEST]->(t1:LabTest)
MATCH (v2)-[:HAD_TEST]->(t2:LabTest)
WHERE t1.test_name = t2.test_name
WITH d.condition AS condition,
     m.name AS medication,
     t1.test_name AS biomarker,
     count(*) AS total_patients_followed,
     sum(CASE WHEN t2.value < t1.value THEN 1 ELSE 0 END) AS improved_cases
RETURN condition,
       medication,
       biomarker,
       total_patients_followed,
       improved_cases,
       round(toFloat(improved_cases) / total_patients_followed * 100, 2) AS betterment_rate_pct
ORDER BY condition, betterment_rate_pct DESC
"""

def compute_medication_betterment():
    driver = get_driver()
    try:
        with driver.session() as session:
            result = session.run(BETTERMENT_RATE_QUERY)
            records = [record.data() for record in result]
            
            print(f"\n{'Condition':<20} | {'Medication':<15} | {'Biomarker':<15} | {'Total':<6} | {'Improved':<8} | {'Betterment %':<12}")
            print("-" * 90)
            for r in records:
                print(
                    f"{r['condition']:<20} | "
                    f"{r['medication']:<15} | "
                    f"{r['biomarker']:<15} | "
                    f"{r['total_patients_followed']:<6} | "
                    f"{r['improved_cases']:<8} | "
                    f"{r['betterment_rate_pct']:<12}%"
                )
    finally:
        driver.close()

if __name__ == "__main__":
    compute_medication_betterment()