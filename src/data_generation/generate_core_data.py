import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

random.seed(42)

def generate_patients(n=50):
    first_names_m = ["James", "Robert", "John", "Michael", "David", "William", "Richard", "Joseph", "Thomas", "Charles"]
    first_names_f = ["Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]

    patients = []
    start_dob = datetime(1950, 1, 1)
    end_dob = datetime(2005, 12, 31)
    delta_days = (end_dob - start_dob).days

    for i in range(1, n + 1):
        pid = f"P{100 + i}"
        gender = random.choice(["M", "F"])
        first = random.choice(first_names_m if gender == "M" else first_names_f)
        last = random.choice(last_names)
        name = f"{first} {last}"
        
        dob_date = start_dob + timedelta(days=random.randint(0, delta_days))
        dob = dob_date.strftime("%Y-%m-%d")
        
        patients.append({"patient_id": pid, "name": name, "dob": dob, "gender": gender})

    filepath = OUTPUT_DIR / "patients.csv"
    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["patient_id", "name", "dob", "gender"])
        writer.writeheader()
        writer.writerows(patients)
    print(f"Generated {len(patients)} patients -> {filepath}")
    return patients

def generate_doctors(n=10):
    specialties = [
        "Cardiology", "Internal Medicine", "Neurology", "Orthopedics",
        "Endocrinology", "Pulmonology", "Gastroenterology", "General Practice"
    ]
    doctor_names = [
        "Dr. Sarah Connor", "Dr. Gregory House", "Dr. John Watson",
        "Dr. Leonard McCoy", "Dr. Meredith Grey", "Dr. Beverly Crusher",
        "Dr. Stephen Strange", "Dr. Shaun Murphy", "Dr. Michaela Quinn",
        "Dr. Martin Ellingham"
    ]
    
    doctors = []
    for i in range(1, n + 1):
        did = f"DOC{200 + i}"
        name = doctor_names[i - 1] if i - 1 < len(doctor_names) else f"Dr. Doctor {i}"
        specialty = random.choice(specialties)
        doctors.append({"doctor_id": did, "name": name, "specialty": specialty})

    filepath = OUTPUT_DIR / "doctors.csv"
    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["doctor_id", "name", "specialty"])
        writer.writeheader()
        writer.writerows(doctors)
    print(f"Generated {len(doctors)} doctors -> {filepath}")
    return doctors

def generate_visits(patients, doctors):
    visits = []
    visit_counter = 301

    # Guarantee multi-visit chronological trajectories
    for patient in patients:
        # Every patient gets 2 to 4 sequential visits
        num_visits = random.randint(2, 4)
        
        # Primary doctor assigned to the patient for consistency
        primary_doctor = random.choice(doctors)
        
        # Start date between Jan 2023 and Jun 2024
        current_date = datetime(2023, 1, 1) + timedelta(days=random.randint(0, 500))
        
        for visit_seq in range(num_visits):
            vid = f"V{visit_counter}"
            visit_counter += 1
            
            # Initial visit is Outpatient/Emergency; subsequent are Follow-ups
            if visit_seq == 0:
                admission = random.choice(["Outpatient", "Emergency", "Inpatient"])
            else:
                admission = "Follow-up"
                # Follow-ups occur 3 to 8 weeks after the prior visit
                current_date += timedelta(days=random.randint(21, 60))
            
            visits.append({
                "visit_id": vid,
                "patient_id": patient["patient_id"],
                "doctor_id": primary_doctor["doctor_id"],
                "visit_date": current_date.strftime("%Y-%m-%d"),
                "admission_type": admission
            })

    filepath = OUTPUT_DIR / "visits.csv"
    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["visit_id", "patient_id", "doctor_id", "visit_date", "admission_type"])
        writer.writeheader()
        writer.writerows(visits)
    print(f"Generated {len(visits)} sequential visits across {len(patients)} patients -> {filepath}")
    return visits

if __name__ == "__main__":
    p = generate_patients(50)
    d = generate_doctors(10)
    generate_visits(p, d)