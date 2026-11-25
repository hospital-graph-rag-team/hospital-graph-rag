import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List

from src.graph.retrieval import get_medication_outcomes


@st.cache_data(ttl=300)
def cached_medication_outcomes(condition: str):
    return get_medication_outcomes(condition)


def render_medication_analytics():
    """
    Renders the Medication Analytics dashboard: cohort-level observational biomarker
    transitions, betterment rates, and therapy outcome distributions.
    """
    st.subheader("Medication Analytics")
    st.caption("Cohort-level observational biomarker shifts across consecutive hospital encounters.")

    # Prominent Academic / Clinical Disclaimer
    st.markdown(
        """
        <div style="background:#FFFBEB; border-left:4px solid #F59E0B; padding:10px 16px; border-radius:0 4px 4px 0; margin-bottom:16px;">
            <strong style="color:#B45309;">⚠️ Observational Association Disclaimer:</strong>
            <span style="color:#78350F; font-size:0.85rem;">
                These statistics represent observational transitions where recorded biomarker values shifted between consecutive encounters.
                They do <strong>NOT</strong> constitute randomized clinical trial data, proof of clinical efficacy, or individual treatment recommendations.
                A higher observational betterment percentage does not imply clinical superiority.
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Condition Selector
    conditions = ["Type 2 Diabetes", "Hypertension", "Hyperlipidemia"]
    selected_condition = st.selectbox(
        "Select Chronic Condition for Analysis:",
        conditions,
        index=0
    )

    try:
        data = cached_medication_outcomes(selected_condition)
    except Exception as e:
        st.error(f"Error retrieving medication outcomes for {selected_condition}: {str(e)}")
        return

    if not data or not data.get("medications"):
        st.info(f"No eligible consecutive visit transitions found for {selected_condition}.")
        return

    biomarker = data.get("biomarker", "Biomarker")
    unit = data.get("unit", "")
    total_transitions = data.get("total_eligible_transitions", 0)
    total_patients = data.get("total_unique_patients", 0)
    medications = data.get("medications", [])

    # Identify highest observed improvement rate (neutral observational label with sample size)
    best_med_info = "N/A"
    if medications:
        top_med = max(medications, key=lambda x: (x.get("betterment_rate_pct", 0), x.get("eligible_transitions", 0)))
        top_rate = top_med.get("betterment_rate_pct", 0)
        top_n = top_med.get("eligible_transitions", 0)
        best_med_info = f"{top_med['medication']} ({top_rate:.1f}%, n={top_n})"

    # KPI Row
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("Analyzed Condition", selected_condition)
    with k2:
        st.metric("Tracked Biomarker", f"{biomarker} ({unit})")
    with k3:
        st.metric("Unique Patients", total_patients, help="Distinct patients with ≥ 1 eligible transition")
    with k4:
        st.metric("Eligible Transitions", total_transitions, help="Consecutive encounter pairs with recorded biomarker values")
    with k5:
        st.metric("Highest Observed Improvement", best_med_info, help="Highest observed percentage of consecutive transitions where biomarker decreased. Does not establish clinical superiority.")

    st.markdown("---")

    # Visualizations Row
    chart_col1, chart_col2 = st.columns(2)

    med_names = [m["medication"] for m in medications]
    betterment_rates = [m["betterment_rate_pct"] for m in medications]
    improved_counts = [m["improved_transitions"] for m in medications]
    worsened_counts = [m["worsened_transitions"] for m in medications]
    unchanged_counts = [m["unchanged_transitions"] for m in medications]
    patient_counts = [m["unique_patient_count"] for m in medications]
    transition_counts = [m["eligible_transitions"] for m in medications]

    with chart_col1:
        st.markdown("#### Observational Betterment Rate (%)")
        st.caption(f"Percentage of transitions where {biomarker} decreased.")

        fig_rate = go.Figure()
        fig_rate.add_trace(go.Bar(
            y=med_names,
            x=betterment_rates,
            orientation="h",
            marker_color="#0D9488",
            text=[f"{r:.1f}%" for r in betterment_rates],
            textposition="auto"
        ))
        fig_rate.update_layout(
            xaxis=dict(title="Betterment Rate (%)", range=[0, 105], gridcolor="#E2E8F0"),
            yaxis=dict(autorange="reversed"),
            margin=dict(l=20, r=20, t=20, b=20),
            height=300,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_rate, use_container_width=True)

    with chart_col2:
        st.markdown("#### Transition Breakdown by Outcome")
        st.caption("Distribution of improved, unchanged, and worsened encounter transitions.")

        fig_dist = go.Figure()
        fig_dist.add_trace(go.Bar(
            name="Improved",
            y=med_names,
            x=improved_counts,
            orientation="h",
            marker_color="#10B981"
        ))
        fig_dist.add_trace(go.Bar(
            name="Unchanged",
            y=med_names,
            x=unchanged_counts,
            orientation="h",
            marker_color="#94A3B8"
        ))
        fig_dist.add_trace(go.Bar(
            name="Worsened",
            y=med_names,
            x=worsened_counts,
            orientation="h",
            marker_color="#F87171"
        ))
        fig_dist.update_layout(
            barmode="stack",
            xaxis=dict(title="Number of Transitions", gridcolor="#E2E8F0"),
            yaxis=dict(autorange="reversed"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=20, b=20),
            height=300,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_dist, use_container_width=True)

    st.markdown("---")

    # Detailed Table
    st.markdown("#### Comprehensive Transition Statistics")
    table_rows = []
    for m in medications:
        table_rows.append({
            "Medication": m["medication"],
            "Unique Patients": m["unique_patient_count"],
            "Eligible Transitions": m["eligible_transitions"],
            "Improved (Biomarker Decreased)": m["improved_transitions"],
            "Worsened (Biomarker Increased)": m["worsened_transitions"],
            "Unchanged": m["unchanged_transitions"],
            "Betterment Rate (%)": f"{m['betterment_rate_pct']:.1f}%"
        })
    st.table(table_rows)

    # Sample Transition Evidence Expander
    with st.expander("🔍 Inspect Underlying Transition Evidence Records"):
        st.caption("Auditable pairwise transitions extracted from Neo4j knowledge graph.")
        for m in medications:
            st.markdown(f"**Medication: {m['medication']}** (Sample Evidence)")
            samples = m.get("evidence_sample", [])
            if samples:
                for s in samples:
                    p_id = s.get("patient_id")
                    v1 = s.get("v1_id")
                    v2 = s.get("v2_id")
                    val1 = s.get("v1_value")
                    val2 = s.get("v2_value")
                    delta = s.get("delta")
                    direction = s.get("direction")
                    rx_id = s.get("prescription_id")
                    st.markdown(
                        f"- Patient `{p_id}` | `{v1}` ({val1} {unit}) ➔ `{v2}` ({val2} {unit}) | "
                        f"Δ: **{delta:+.2f}** (`{direction}`) | Prescription: `{rx_id}`"
                    )
            else:
                st.caption("No sample records available.")
