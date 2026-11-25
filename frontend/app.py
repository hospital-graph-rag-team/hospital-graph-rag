import sys
import os
from pathlib import Path

# Ensure repository root and src are on sys.path regardless of execution directory
ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

for p in [str(ROOT_DIR), str(SRC_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import streamlit as st

from frontend.styles import apply_custom_styles, render_academic_notice
from frontend.components.dashboard import render_hospital_overview
from frontend.components.patient_view import render_patient_explorer
from frontend.components.graph_view import render_patient_graph_view
from frontend.components.chat import render_ai_assistant
from frontend.components.analytics import render_medication_analytics

from src.graph.retrieval import get_patient_directory
from src.graph.connection import get_driver


# -------------------------------------------------------------
# Streamlit Application Configuration
# -------------------------------------------------------------
st.set_page_config(
    page_title="ClinicalGraph — Hospital Graph RAG",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_custom_styles()


# -------------------------------------------------------------
# Cached Data Loaders
# -------------------------------------------------------------
@st.cache_data(ttl=300)
def load_cached_patient_directory():
    """Retrieves and caches the list of 50 patients with a 5-minute TTL."""
    try:
        return get_patient_directory()
    except Exception:
        return []


def check_database_status():
    """Verifies live read-only connectivity to Neo4j AuraDB."""
    try:
        driver = get_driver()
        with driver.session() as s:
            res = s.run("RETURN 1 AS ping").single()
            return res and res["ping"] == 1
    except Exception:
        return False


# -------------------------------------------------------------
# Main Application Layout
# -------------------------------------------------------------
def main():
    render_academic_notice()

    # Sidebar Construction
    with st.sidebar:
        st.markdown("## 🏥 ClinicalGraph")
        st.caption("Hospital Graph RAG & Clinical Intelligence")
        st.markdown("---")

        # Navigation Controls with query parameter support
        nav_options = [
            "Hospital Overview",
            "Patient Explorer",
            "Patient Knowledge Graph",
            "AI Assistant",
            "Medication Analytics"
        ]
        
        qp_nav = st.query_params.get("nav")
        default_nav_idx = 0
        if qp_nav and qp_nav in nav_options:
            default_nav_idx = nav_options.index(qp_nav)

        selected_nav = st.radio(
            "Navigation",
            nav_options,
            index=default_nav_idx
        )

        st.markdown("---")

        # Searchable Patient Selection with query parameter support
        st.markdown("### Patient Selection")
        patients = load_cached_patient_directory()

        patient_options = ["(None / General Cohort)"] + [
            f"{p['patient_id']} — {p['name']}" for p in patients
        ]

        qp_patient = st.query_params.get("patient_id")
        default_patient_idx = 0
        if qp_patient:
            for idx, opt in enumerate(patient_options):
                if opt.startswith(f"{qp_patient} "):
                    default_patient_idx = idx
                    break

        selected_patient_str = st.selectbox(
            "Select Patient:",
            patient_options,
            index=default_patient_idx,
            key="patient_selector",
            help="Choose a patient to inspect their profile, timeline, biomarkers, or graph relationships."
        )

        # Update Session State & Detect Context Switch
        if selected_patient_str and not selected_patient_str.startswith("("):
            selected_patient_id = selected_patient_str.split(" — ")[0].strip()
            matched_patient = next((p for p in patients if p["patient_id"] == selected_patient_id), None)
        else:
            selected_patient_id = None
            matched_patient = None

        # Isolate conversation history when patient context changes
        if st.session_state.get("selected_patient_id") != selected_patient_id:
            st.session_state["messages"] = []
            st.session_state["chat_patient_id"] = selected_patient_id

        st.session_state["selected_patient_id"] = selected_patient_id
        st.session_state["selected_patient_name"] = matched_patient["name"] if matched_patient else ""

        # Display Quick Patient Context in Sidebar
        if matched_patient:
            st.markdown(
                f"""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px; padding:10px; margin-top:8px;">
                    <span style="font-size:0.75rem; color:#64748B; font-weight:600;">ACTIVE PATIENT</span>
                    <div style="font-weight:700; color:#0F172A; font-size:0.95rem;">{matched_patient['name']}</div>
                    <div style="font-size:0.8rem; color:#334155;">ID: <code>{matched_patient['patient_id']}</code></div>
                    <div style="font-size:0.8rem; color:#64748B;">{matched_patient['gender']} • DOB: {matched_patient['dob']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("---")

        # Database Status Indicator
        is_connected = check_database_status()
        if is_connected:
            st.markdown("🟢 **Neo4j AuraDB:** Connected")
        else:
            st.markdown("🔴 **Neo4j AuraDB:** Disconnected")

        st.markdown("🤖 **Groq Model:** `gpt-oss-120b`")

        # Cache Refresh
        if st.button("🔄 Refresh Data Cache", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        st.caption("Hospital Graph RAG • Person 2 Deliverable")

    # Main Area View Dispatcher
    if selected_nav == "Hospital Overview":
        render_hospital_overview()
    elif selected_nav == "Patient Explorer":
        render_patient_explorer(selected_patient_id)
    elif selected_nav == "Patient Knowledge Graph":
        render_patient_graph_view(selected_patient_id)
    elif selected_nav == "AI Assistant":
        render_ai_assistant(selected_patient_id)
    elif selected_nav == "Medication Analytics":
        render_medication_analytics()


if __name__ == "__main__":
    main()
