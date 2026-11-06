import pandas as pd
import numpy as np
from pathlib import Path

# Resolve data/raw directory relative to src/data_generation
ROOT_DIR = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = ROOT_DIR / "data" / "raw"

# Chronic conditions, target biomarkers, and typical medications
DISEASE_PROFILES = {
    "Type 2 Diabetes": {
        "biomarker": "HbA1c",
        "unit": "%",
        "baseline_range": (8.0, 11.0),
        "target_range": (5.7, 7.0),
        "medications": ["Metformin", "Glipizide", "Empagliflozin"]
    },
    "Hypertension": {
        "biomarker": "Systolic BP",
        "unit": "mmHg",
        "baseline_range": (145.0, 180.0),
        "target_range": (115.0, 130.0),
        "medications": ["Amlodipine", "Lisinopril", "Losartan"]
    },
    "Hyperlipidemia": {
        "biomarker": "LDL Cholesterol",
        "unit": "mg/dL",
        "baseline_range": (160.0, 220.0),
        "target_range": (70.0, 100.0),
        "medications": ["Atorvastatin", "Rosuvastatin", "Simvastatin"]
    }
}

def generate_clinical_records():
    visits_df = pd.read_csv(RAW_DATA_DIR / "visits.csv")
    patients_df = pd.read_csv(RAW_DATA_DIR / "patients.csv")
    
    # Sort visits by patient and date to model chronological treatment response
    visits_df["visit_date"] = pd.to_datetime(visits_df["visit_date"])
    visits_df = visits_df.sort_values(by=["patient_id", "visit_date"]).reset_index(drop=True)
    
    np.random.seed(42)
    diseases = list(DISEASE_PROFILES.keys())
    patient_disease_map = {
        pid: np.random.choice(diseases) for pid in patients_df["patient_id"]
    }

    diagnoses = []
    medications = []
    lab_tests = []
    
    diag_id_counter = 1
    med_id_counter = 1
    lab_id_counter = 1

    patient_state = {}

    for _, visit in visits_df.iterrows():
        vid = visit["visit_id"]
        pid = visit["patient_id"]
        disease_name = patient_disease_map[pid]
        profile = DISEASE_PROFILES[disease_name]

        # 1. Attach Diagnosis
        diagnoses.append({
            "diagnosis_id": f"D{diag_id_counter:04d}",
            "visit_id": vid,
            "condition": disease_name,
            "status": "Active"
        })
        diag_id_counter += 1

        # 2. Check if baseline or follow-up encounter
        if pid not in patient_state:
            baseline_val = np.round(np.random.uniform(*profile["baseline_range"]), 1)
            med = np.random.choice(profile["medications"])
            effective = bool(np.random.choice([True, False], p=[0.75, 0.25]))

            patient_state[pid] = {
                "current_val": baseline_val,
                "active_med": med,
                "is_effective": effective,
                "profile": profile
            }
        else:
            state = patient_state[pid]
            if state["is_effective"]:
                target_min, _ = state["profile"]["target_range"]
                drop_factor = np.random.uniform(0.15, 0.30)
                new_val = state["current_val"] * (1 - drop_factor)
                state["current_val"] = np.round(max(new_val, target_min + np.random.uniform(0, 0.5)), 1)
            else:
                state["current_val"] = np.round(state["current_val"] + np.random.uniform(-1.0, 3.0), 1)

        current_info = patient_state[pid]

        # 3. Attach Medication
        medications.append({
            "prescription_id": f"RX{med_id_counter:04d}",
            "visit_id": vid,
            "medication_name": current_info["active_med"],
            "dosage": "Standard",
            "is_effective": current_info["is_effective"]
        })
        med_id_counter += 1

        # 4. Attach Lab Test / Biomarker reading
        lab_tests.append({
            "test_id": f"T{lab_id_counter:04d}",
            "visit_id": vid,
            "test_name": profile["biomarker"],
            "value": current_info["current_val"],
            "unit": profile["unit"]
        })
        lab_id_counter += 1

    # Export to data/raw/
    pd.DataFrame(diagnoses).to_csv(RAW_DATA_DIR / "diagnoses.csv", index=False)
    pd.DataFrame(medications).to_csv(RAW_DATA_DIR / "medications.csv", index=False)
    pd.DataFrame(lab_tests).to_csv(RAW_DATA_DIR / "lab_tests.csv", index=False)

    print(f"✓ Created {len(diagnoses)} records -> data/raw/diagnoses.csv")
    print(f"✓ Created {len(medications)} records -> data/raw/medications.csv")
    print(f"✓ Created {len(lab_tests)} records -> data/raw/lab_tests.csv")

if __name__ == "__main__":
    generate_clinical_records()