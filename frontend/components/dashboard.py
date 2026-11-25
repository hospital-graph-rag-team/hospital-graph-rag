import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any

from src.graph.retrieval import get_hospital_overview_stats


@st.cache_data(ttl=300)
def cached_hospital_overview_stats():
    """Cached read-only retrieval of cohort overview stats with 5m TTL."""
    return get_hospital_overview_stats()


def render_hospital_overview():
    """
    Renders the Hospital Overview dashboard displaying dynamically retrieved
    knowledge graph statistics, condition distributions, and admission types.
    """
    st.subheader("Hospital Overview")
    st.caption("Live cohort metrics retrieved dynamically from the Neo4j Knowledge Graph.")

    try:
        stats = cached_hospital_overview_stats()
    except Exception as e:
        st.error(f"Failed to connect to Neo4j Knowledge Graph: {str(e)}")
        st.info("Please verify your `.env` configuration and AuraDB network status.")
        return

    totals = stats.get("totals", {})
    conditions = stats.get("conditions", [])
    admission_types = stats.get("admission_types", [])

    # Row 1: Core clinical entities
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Patients", f"{totals.get('total_patients', 0):,}", help="Unique patient entities in graph")
    with c2:
        st.metric("Total Doctors", f"{totals.get('total_doctors', 0):,}", help="Attending physicians")
    with c3:
        st.metric("Total Visits", f"{totals.get('total_visits', 0):,}", help="Inpatient, Outpatient, Emergency & Follow-ups")
    with c4:
        st.metric("Lab Test Records", f"{totals.get('total_lab_records', 0):,}", help="Individual laboratory observations")

    # Row 2: Graph schema & relationship totals
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.metric("Diagnosis Records", f"{totals.get('total_diagnosis_records', 0):,}", help="Encounter diagnoses (linked to 3 shared condition nodes)")
    with c6:
        st.metric("Prescription Records", f"{totals.get('total_prescription_records', 0):,}", help="Prescription events (linked to 9 shared medication nodes)")
    with c7:
        st.metric("Graph Nodes", f"{totals.get('total_nodes', 0):,}", help="Total nodes across all 6 labels")
    with c8:
        st.metric("Graph Relationships", f"{totals.get('total_relationships', 0):,}", help="Total edges across all 6 relationship types")

    st.markdown("---")

    # Charts Row
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("#### Patient Distribution by Condition")
        st.caption("Unique patients and total encounter records per chronic diagnosis.")
        if conditions:
            cond_names = [c["condition"] for c in conditions]
            patient_counts = [c["patient_count"] for c in conditions]
            record_counts = [c["record_count"] for c in conditions]

            fig_cond = go.Figure()
            fig_cond.add_trace(go.Bar(
                x=cond_names,
                y=patient_counts,
                name="Unique Patients",
                marker_color="#0D9488",
                text=patient_counts,
                textposition="auto"
            ))
            fig_cond.add_trace(go.Bar(
                x=cond_names,
                y=record_counts,
                name="Total Encounter Records",
                marker_color="#3B82F6",
                text=record_counts,
                textposition="auto"
            ))
            fig_cond.update_layout(
                barmode="group",
                margin=dict(l=20, r=20, t=20, b=20),
                height=320,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(gridcolor="#E2E8F0"),
                xaxis=dict(gridcolor="#E2E8F0")
            )
            st.plotly_chart(fig_cond, use_container_width=True)
        else:
            st.info("No condition data retrieved.")

    with chart_col2:
        st.markdown("#### Encounter Distribution by Admission Type")
        st.caption("Breakdown of 146 hospital encounters across care settings.")
        if admission_types:
            adm_labels = [a["admission_type"] for a in admission_types]
            adm_values = [a["count"] for a in admission_types]
            colors = ["#0D9488", "#2563EB", "#F59E0B", "#DC2626"]

            fig_adm = px.pie(
                names=adm_labels,
                values=adm_values,
                color_discrete_sequence=colors,
                hole=0.45
            )
            fig_adm.update_traces(textposition="inside", textinfo="percent+label")
            fig_adm.update_layout(
                margin=dict(l=20, r=20, t=20, b=20),
                height=320,
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_adm, use_container_width=True)
        else:
            st.info("No admission type data retrieved.")

    st.markdown("---")

    # Architecture Explanation Section
    st.markdown("#### How Clinical Graph RAG Works")
    st.markdown(
        """
        Unlike standard vector RAG systems that split documents into isolated text chunks,
        **ClinicalGraph** couples an expressive **Neo4j Property Graph** with a **Groq ReAct Agent** (`openai/gpt-oss-120b`):
        
        1. **Deterministic Subgraph Retrieval:** Longitudinal clinical pathways (`FOLLOWED_BY`), doctor encounters (`ATTENDED_BY`),
           medication events (`PRESCRIBED`), and lab readings (`HAD_TEST`) are queried via strict Cypher graph traversals.
        2. **Multi-Hop Synthesis:** The ReAct agent resolves complex multi-entity questions (e.g., patient disambiguation, consecutive visit biomarker trajectories, cohort medication betterment) by dispatching discrete tool calls.
        3. **Grounded Auditing:** Every factual response is anchored to concrete graph entities (e.g. `P101`, `V301`, `RX0001`, `T0001`), with automated citation verification validating identifiers against retrieved evidence.
        """
    )
