import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, date
from typing import Optional, Dict, Any, List

from src.graph.retrieval import (
    get_patient_profile,
    get_patient_timeline,
    get_lab_trends,
    get_followup_comparison
)


@st.cache_data(ttl=300)
def cached_patient_profile(patient_id: str):
    return get_patient_profile(patient_id)


@st.cache_data(ttl=300)
def cached_patient_timeline(patient_id: str):
    return get_patient_timeline(patient_id)


@st.cache_data(ttl=300)
def cached_lab_trends(patient_id: str):
    return get_lab_trends(patient_id)


@st.cache_data(ttl=300)
def cached_followup_comparison(patient_id: str):
    return get_followup_comparison(patient_id)


def render_patient_explorer(selected_patient_id: Optional[str]):
    """
    Renders the Patient Explorer view: demographics, encounter timeline,
    longitudinal biomarker trends, and consecutive follow-up comparisons.
    """
    st.subheader("Patient Explorer")

    if not selected_patient_id:
        st.info("Please select a patient from the sidebar to inspect their clinical profile and longitudinal timeline.")
        return

    # 1. Patient Profile Demographics
    try:
        profile = cached_patient_profile(selected_patient_id)
    except Exception as e:
        st.error(f"Error loading profile for {selected_patient_id}: {str(e)}")
        return

    if not profile:
        st.warning(f"Patient {selected_patient_id} was not found in the hospital knowledge graph.")
        return

    # Calculate derived age from DOB
    dob_val = profile.get("dob")
    age_str = "N/A"
    if dob_val:
        try:
            dob_d = datetime.fromisoformat(str(dob_val)).date()
            today_d = date.today()
            calc_age = today_d.year - dob_d.year - ((today_d.month, today_d.day) < (dob_d.month, dob_d.day))
            age_str = f"{calc_age} yrs (derived)"
        except Exception:
            age_str = "N/A"

    # Header Card
    with st.container():
        st.markdown(
            f"""
            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:16px 20px; margin-bottom:16px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h2 style="margin:0; font-size:1.4rem; color:#0F172A;">{profile.get('name', 'Unknown')}</h2>
                        <span style="font-family:monospace; background:#E0F2FE; color:#0369A1; padding:2px 8px; border-radius:4px; font-weight:600; font-size:0.85rem;">
                            ID: {profile.get('patient_id', selected_patient_id)}
                        </span>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:0.85rem; color:#64748B;">Gender: <strong>{profile.get('gender', 'N/A')}</strong></span> |
                        <span style="font-size:0.85rem; color:#64748B;">DOB: <strong>{profile.get('dob', 'N/A')}</strong></span> |
                        <span style="font-size:0.85rem; color:#64748B;">Age: <strong>{age_str}</strong></span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Encounter Summary KPI
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Encounters", profile.get("visit_count", profile.get("total_visits", 0)))
    with col2:
        st.metric("First Recorded Visit", profile.get("first_visit_date", "N/A"))
    with col3:
        st.metric("Latest Recorded Visit", profile.get("latest_visit_date", "N/A"))

    st.markdown("---")

    # Tabs for Timeline, Trends, Follow-ups
    tab_timeline, tab_trends, tab_followup = st.tabs([
        "Clinical Visit Timeline",
        "Laboratory Trends",
        "Follow-Up Comparisons"
    ])

    # -------------------------------------------------------------
    # TAB 1: Clinical Visit Timeline
    # -------------------------------------------------------------
    with tab_timeline:
        st.markdown("#### Chronological Encounter Trajectory")
        st.caption("Visits, attending physicians, active diagnoses, prescriptions, and laboratory observations.")

        try:
            timeline = cached_patient_timeline(selected_patient_id)
        except Exception as e:
            st.error(f"Error fetching timeline: {str(e)}")
            timeline = []

        if not timeline:
            st.info("No recorded hospital encounters found for this patient.")
        else:
            for idx, visit in enumerate(timeline, 1):
                vid = visit.get("visit_id")
                vdate = visit.get("visit_date")
                adm_type = visit.get("admission_type", "Standard")
                doc = visit.get("doctor") if isinstance(visit.get("doctor"), dict) else {}
                doc_name = doc.get("name") or visit.get("doctor_name", "Unassigned")
                doc_id = doc.get("doctor_id") or visit.get("doctor_id", "")
                specialty = doc.get("specialty") or visit.get("specialty", "")

                with st.expander(f"Encounter #{idx} — Visit {vid} on {vdate} ({adm_type})", expanded=(idx == 1)):
                    st.markdown(f"**Attending Physician:** {doc_name} (`{doc_id}`) — *{specialty}*")

                    sub_col1, sub_col2, sub_col3 = st.columns(3)

                    with sub_col1:
                        st.markdown("**Diagnoses**")
                        diagnoses = visit.get("diagnoses", [])
                        if diagnoses:
                            for d in diagnoses:
                                status = d.get("status", "Active")
                                st.markdown(f"- **{d.get('condition')}** (`{d.get('diagnosis_id')}`) — *{status}*")
                        else:
                            st.caption("No diagnosis recorded")

                    with sub_col2:
                        st.markdown("**Prescriptions**")
                        medications = visit.get("medications") or visit.get("prescriptions", [])
                        if medications:
                            for p in medications:
                                med_name = p.get("medication_name") or p.get("medication", "Unknown")
                                rx_id = p.get("prescription_id", "N/A")
                                dosage = p.get("dosage", "Standard")
                                is_eff = p.get("is_effective") if "is_effective" in p else p.get("effective", False)
                                eff_str = "Effective" if is_eff else "Not effective"
                                st.markdown(f"- **{med_name}** (`{rx_id}`)<br>&nbsp;&nbsp;Dosage: {dosage}<br>&nbsp;&nbsp;*{eff_str}*", unsafe_allow_html=True)
                        else:
                            st.caption("No medication prescribed")

                    with sub_col3:
                        st.markdown("**Laboratory Tests**")
                        lab_tests = visit.get("lab_tests", [])
                        if lab_tests:
                            for t in lab_tests:
                                st.markdown(f"- **{t.get('test_name')}** (`{t.get('test_id')}`): **{t.get('value')} {t.get('unit')}**")
                        else:
                            st.caption("No lab test performed")

    # -------------------------------------------------------------
    # TAB 2: Laboratory Trends
    # -------------------------------------------------------------
    with tab_trends:
        st.markdown("#### Quantitative Biomarker Trajectories")
        st.caption("Longitudinal tracking of blood biomarkers across consecutive encounters.")

        try:
            lab_groups = cached_lab_trends(selected_patient_id)
        except Exception as e:
            st.error(f"Error fetching lab trends: {str(e)}")
            lab_groups = []

        if not lab_groups:
            st.info("No laboratory measurements available for longitudinal tracking.")
        else:
            test_options = [g.get("biomarker") or g.get("test_name", "Unknown") for g in lab_groups]
            selected_test = st.selectbox("Select Laboratory Biomarker:", test_options, index=0)

            # Find matching group
            group = next((g for g in lab_groups if (g.get("biomarker") or g.get("test_name")) == selected_test), lab_groups[0])
            obs_count = group.get("observation_count", 0)
            unit = group.get("unit", "")
            direction = group.get("direction", "unknown")
            measurements = group.get("observations") or group.get("measurements", [])

            # KPI Metrics Row
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            with m_col1:
                st.metric("Total Readings", obs_count)
            with m_col2:
                st.metric("Initial Value", f"{group.get('initial_value')} {unit}" if group.get('initial_value') is not None else "N/A")
            with m_col3:
                st.metric("Latest Value", f"{group.get('latest_value')} {unit}" if group.get('latest_value') is not None else "N/A")
            with m_col4:
                if direction == "insufficient_data":
                    st.metric("Trajectory Status", "Single Observation", help="Only one observation available; trend cannot be computed.")
                else:
                    pct = group.get("percentage_change")
                    pct_str = f"{pct:+.1f}%" if pct is not None else "N/A"
                    st.metric("Trajectory Status", direction.capitalize(), delta=pct_str, delta_color="off")

            # Chart rendering
            if obs_count <= 1:
                st.info(f"Only a single observation ({group.get('initial_value')} {unit}) was recorded for {selected_test}. Longitudinal trend requires ≥ 2 encounters.")
            else:
                dates = [m.get("visit_date") or m.get("date") for m in measurements]
                values = [m.get("value") for m in measurements]
                hover_texts = [
                    f"Visit: {m.get('visit_id')}<br>Test ID: {m.get('test_id')}<br>Date: {m.get('visit_date') or m.get('date')}<br>Value: {m.get('value')} {unit}"
                    for m in measurements
                ]

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=values,
                    mode="lines+markers",
                    name=selected_test,
                    line=dict(color="#0D9488", width=3),
                    marker=dict(size=9, color="#0F172A", symbol="circle"),
                    text=hover_texts,
                    hoverinfo="text"
                ))
                fig.update_layout(
                    title=f"{selected_test} Progression Over Time",
                    xaxis_title="Encounter Date",
                    yaxis_title=f"{selected_test} ({unit})",
                    margin=dict(l=20, r=20, t=40, b=20),
                    height=340,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(gridcolor="#E2E8F0"),
                    yaxis=dict(gridcolor="#E2E8F0")
                )
                st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------------------
    # TAB 3: Follow-Up Comparison
    # -------------------------------------------------------------
    with tab_followup:
        st.markdown("#### Consecutive Encounter Progression (FOLLOWED_BY)")
        st.caption("Pairwise visit analysis tracking interval duration, therapy adjustments, and biomarker shifts.")

        try:
            followups = cached_followup_comparison(selected_patient_id)
        except Exception as e:
            st.error(f"Error fetching follow-up comparison: {str(e)}")
            followups = []

        if not followups:
            st.info("No consecutive visit pairs (FOLLOWED_BY relationships) exist for this patient.")
        else:
            for idx, pair in enumerate(followups, 1):
                v1 = pair.get("previous_visit") or {}
                v2 = pair.get("followup_visit") or {}
                v1_id = v1.get("visit_id", pair.get("v1_id"))
                v2_id = v2.get("visit_id", pair.get("v2_id"))
                v1_date = v1.get("visit_date", pair.get("v1_date"))
                v2_date = v2.get("visit_date", pair.get("v2_date"))
                days = pair.get("days_between")
                
                v1_diag = v1.get("diagnoses", [])
                condition = v1_diag[0].get("condition") if v1_diag else pair.get("condition", "N/A")
                
                v2_meds = v2.get("prescriptions") or v2.get("medications", [])
                med = v2_meds[0].get("medication_name") if v2_meds else pair.get("medication_v2", "N/A")
                
                lab_comps = pair.get("lab_comparisons", [])
                primary_comp = lab_comps[0] if lab_comps else {}
                test_name = primary_comp.get("biomarker", pair.get("test_name", "Biomarker"))
                unit = primary_comp.get("unit", pair.get("unit", ""))
                v1_val = primary_comp.get("v1_value", pair.get("v1_value"))
                v2_val = primary_comp.get("v2_value", pair.get("v2_value"))
                delta = primary_comp.get("absolute_change", pair.get("absolute_delta"))
                pct = primary_comp.get("percentage_change", pair.get("percentage_change"))
                direction = primary_comp.get("direction", pair.get("direction", "unchanged"))

                with st.expander(f"Transition #{idx}: {v1_id} ({v1_date}) ➔ {v2_id} ({v2_date}) — Interval: {days} days", expanded=True):
                    fc1, fc2, fc3 = st.columns(3)
                    with fc1:
                        st.markdown(f"**Diagnosis:** {condition}")
                        st.markdown(f"**Therapy (V2):** {med}")
                    with fc2:
                        st.markdown(f"**Biomarker:** {test_name}")
                        st.markdown(f"Baseline: **{v1_val} {unit}**<br>Follow-up: **{v2_val} {unit}**", unsafe_allow_html=True)
                    with fc3:
                        delta_str = f"{delta:+.2f} {unit}" if delta is not None else "N/A"
                        pct_str = f"{pct:+.1f}%" if pct is not None else "N/A"
                        st.markdown(f"**Shift:** {delta_str} ({pct_str})")
                        st.markdown(f"**Direction:** `{direction}`")
