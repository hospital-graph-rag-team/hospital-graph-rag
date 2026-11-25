import streamlit as st
import plotly.graph_objects as go
from typing import Optional, Dict, Any, List, Tuple

from src.graph.retrieval import get_patient_timeline, get_patient_profile
from frontend.components.patient_view import cached_patient_timeline, cached_patient_profile


def build_patient_knowledge_graph(patient_id: str, timeline: List[Dict[str, Any]], profile: Optional[Dict[str, Any]]) -> go.Figure:
    """
    Constructs an interactive 2D network visualization representing the patient's
    local knowledge graph in Neo4j, preserving shared entity nodes (Doctor, Diagnosis,
    Medication) and representing relationships (HAD_VISIT, ATTENDED_BY, FOLLOWED_BY,
    DIAGNOSED_WITH, PRESCRIBED, HAD_TEST).
    """
    # 1. Collect unique nodes & deduplicate shared entities
    patient_name = profile.get("name", "Patient") if profile else "Patient"
    patient_node = {
        "id": patient_id,
        "type": "Patient",
        "label": f"{patient_name} ({patient_id})",
        "hover": f"<b>Patient:</b> {patient_name}<br><b>ID:</b> {patient_id}<br><b>DOB:</b> {profile.get('dob', 'N/A') if profile else 'N/A'}"
    }

    visit_nodes = []
    doctor_nodes = {}
    diagnosis_nodes = {}
    medication_nodes = {}
    lab_nodes = {}

    edges = []

    for v_idx, visit in enumerate(timeline):
        vid = visit["visit_id"]
        vdate = visit.get("visit_date", "")
        adm = visit.get("admission_type", "")
        visit_nodes.append({
            "id": vid,
            "type": "Visit",
            "label": f"{vid} ({vdate})",
            "hover": f"<b>Visit:</b> {vid}<br><b>Date:</b> {vdate}<br><b>Admission:</b> {adm}",
            "order": v_idx
        })

        # Relationship: Patient -[:HAD_VISIT]-> Visit
        edges.append({
            "source": patient_id,
            "target": vid,
            "rel": "HAD_VISIT",
            "hover": f"HAD_VISIT<br>{patient_id} ➔ {vid}"
        })

        # Consecutive Visit Relationship: Visit_i -[:FOLLOWED_BY]-> Visit_{i+1}
        if v_idx > 0:
            prev_vid = timeline[v_idx - 1]["visit_id"]
            edges.append({
                "source": prev_vid,
                "target": vid,
                "rel": "FOLLOWED_BY",
                "hover": f"FOLLOWED_BY<br>{prev_vid} ➔ {vid}"
            })

        # Doctor: Visit -[:ATTENDED_BY]-> Doctor (Shared)
        doc = visit.get("doctor") if isinstance(visit.get("doctor"), dict) else {}
        doc_id = doc.get("doctor_id") or visit.get("doctor_id")
        doc_name = doc.get("name") or visit.get("doctor_name", "Unassigned")
        specialty = doc.get("specialty") or visit.get("specialty", "")
        if doc_id:
            if doc_id not in doctor_nodes:
                doctor_nodes[doc_id] = {
                    "id": doc_id,
                    "type": "Doctor",
                    "label": f"{doc_name} ({doc_id})",
                    "hover": f"<b>Physician:</b> {doc_name}<br><b>ID:</b> {doc_id}<br><b>Specialty:</b> {specialty}"
                }
            edges.append({
                "source": vid,
                "target": doc_id,
                "rel": "ATTENDED_BY",
                "hover": f"ATTENDED_BY<br>{vid} ➔ {doc_id}"
            })

        # Diagnoses: Visit -[:DIAGNOSED_WITH]-> Diagnosis (Shared)
        for d in visit.get("diagnoses", []):
            cond = d.get("condition")
            diag_id = d.get("diagnosis_id")
            status = d.get("status", "Active")
            if cond:
                if cond not in diagnosis_nodes:
                    diagnosis_nodes[cond] = {
                        "id": cond,
                        "type": "Diagnosis",
                        "label": cond,
                        "hover": f"<b>Diagnosis (Condition):</b> {cond}"
                    }
                edges.append({
                    "source": vid,
                    "target": cond,
                    "rel": "DIAGNOSED_WITH",
                    "hover": f"DIAGNOSED_WITH<br>Record: {diag_id}<br>Status: {status}"
                })

        # Prescriptions / Medications: Visit -[:PRESCRIBED]-> Medication (Shared)
        med_list = visit.get("medications") or visit.get("prescriptions", [])
        for p in med_list:
            med = p.get("medication_name") or p.get("medication")
            rx_id = p.get("prescription_id", "N/A")
            dosage = p.get("dosage", "Standard")
            is_eff = p.get("is_effective") if "is_effective" in p else p.get("effective", False)
            effective = "Yes" if is_eff else "No"
            if med:
                if med not in medication_nodes:
                    medication_nodes[med] = {
                        "id": med,
                        "type": "Medication",
                        "label": med,
                        "hover": f"<b>Medication:</b> {med}"
                    }
                edges.append({
                    "source": vid,
                    "target": med,
                    "rel": "PRESCRIBED",
                    "hover": f"PRESCRIBED<br>Rx ID: {rx_id}<br>Dosage: {dosage}<br>Effective: {effective}"
                })

        # Lab Tests: Visit -[:HAD_TEST]-> LabTest (Individual)
        for t in visit.get("lab_tests", []):
            tid = t.get("test_id")
            tname = t.get("test_name")
            val = t.get("value")
            unit = t.get("unit")
            if tid:
                lab_nodes[tid] = {
                    "id": tid,
                    "type": "LabTest",
                    "label": f"{tname}: {val} {unit}",
                    "hover": f"<b>Lab Test:</b> {tname}<br><b>ID:</b> {tid}<br><b>Value:</b> {val} {unit}"
                }
                edges.append({
                    "source": vid,
                    "target": tid,
                    "rel": "HAD_TEST",
                    "hover": f"HAD_TEST<br>{vid} ➔ {tid} ({tname})"
                })

    # 2. Compute 2D coordinates in layered columns
    # Col 0 (x=0): Patient
    # Col 1 (x=2.5): Visits
    # Col 2 (x=5.5): Clinical Entities (Doctors, Diagnoses, Medications, Lab Tests)
    node_coords: Dict[str, Tuple[float, float]] = {}
    node_coords[patient_id] = (0.0, 0.0)

    n_visits = max(1, len(visit_nodes))
    for i, v in enumerate(visit_nodes):
        y_pos = (n_visits - 1) / 2.0 - i
        node_coords[v["id"]] = (2.5, y_pos * 2.2)

    # Gather right-hand entity nodes
    right_nodes = (
        list(doctor_nodes.values()) +
        list(diagnosis_nodes.values()) +
        list(medication_nodes.values()) +
        list(lab_nodes.values())
    )
    n_right = max(1, len(right_nodes))
    for j, rn in enumerate(right_nodes):
        y_pos = (n_right - 1) / 2.0 - j
        node_coords[rn["id"]] = (5.5, y_pos * 1.3)

    # 3. Create Edge Traces
    edge_x = []
    edge_y = []
    edge_mid_x = []
    edge_mid_y = []
    edge_mid_hover = []

    for edge in edges:
        s_pos = node_coords.get(edge["source"])
        t_pos = node_coords.get(edge["target"])
        if s_pos and t_pos:
            edge_x.extend([s_pos[0], t_pos[0], None])
            edge_y.extend([s_pos[1], t_pos[1], None])
            # Midpoint for relationship hover detail
            edge_mid_x.append((s_pos[0] + t_pos[0]) / 2.0)
            edge_mid_y.append((s_pos[1] + t_pos[1]) / 2.0)
            edge_mid_hover.append(edge["hover"])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1.5, color="#CBD5E1"),
        hoverinfo="none",
        mode="lines",
        showlegend=False
    )

    edge_mid_trace = go.Scatter(
        x=edge_mid_x,
        y=edge_mid_y,
        mode="markers",
        marker=dict(size=6, color="#94A3B8", symbol="diamond"),
        hoverinfo="text",
        hovertext=edge_mid_hover,
        name="Relationships",
        showlegend=False
    )

    # 4. Create Node Traces by Entity Type (for distinct colors and automatic legend)
    colors = {
        "Patient": "#0F172A",     # Navy
        "Visit": "#0D9488",       # Teal
        "Doctor": "#2563EB",      # Blue
        "Diagnosis": "#DC2626",   # Red
        "Medication": "#7C3AED",  # Violet
        "LabTest": "#059669"      # Emerald
    }
    sizes = {
        "Patient": 24,
        "Visit": 18,
        "Doctor": 14,
        "Diagnosis": 16,
        "Medication": 16,
        "LabTest": 14
    }

    all_nodes_by_type = {
        "Patient": [patient_node],
        "Visit": visit_nodes,
        "Doctor": list(doctor_nodes.values()),
        "Diagnosis": list(diagnosis_nodes.values()),
        "Medication": list(medication_nodes.values()),
        "LabTest": list(lab_nodes.values())
    }

    traces = [edge_trace, edge_mid_trace]

    for entity_type, nodes in all_nodes_by_type.items():
        if not nodes:
            continue
        xs = [node_coords[n["id"]][0] for n in nodes if n["id"] in node_coords]
        ys = [node_coords[n["id"]][1] for n in nodes if n["id"] in node_coords]
        labels = [n["label"] for n in nodes if n["id"] in node_coords]
        hovers = [n["hover"] for n in nodes if n["id"] in node_coords]

        trace = go.Scatter(
            x=xs,
            y=ys,
            mode="markers+text",
            name=f"{entity_type} ({len(nodes)})",
            marker=dict(
                size=sizes[entity_type],
                color=colors[entity_type],
                line=dict(width=1.5, color="#FFFFFF")
            ),
            text=labels,
            textposition="top center",
            textfont=dict(size=10, color="#1E293B"),
            hoverinfo="text",
            hovertext=hovers
        )
        traces.append(trace)

    fig = go.Figure(data=traces)
    fig.update_layout(
        title=f"Knowledge Graph Subgraph: Patient {patient_id}",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=20, r=20, t=60, b=20),
        height=520,
        hovermode="closest",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
    )

    return fig


def render_patient_graph_view(selected_patient_id: Optional[str]):
    """
    Renders the interactive Plotly knowledge graph visualization tab for the selected patient.
    """
    st.subheader("Patient Knowledge Graph Visualization")
    st.caption("Interactive subgraph representation linking encounters, care providers, active conditions, therapies, and laboratory findings.")

    if not selected_patient_id:
        st.info("Please select a patient from the sidebar to inspect their knowledge graph representation.")
        return

    try:
        timeline = cached_patient_timeline(selected_patient_id)
        profile = cached_patient_profile(selected_patient_id)
    except Exception as e:
        st.error(f"Error fetching graph data: {str(e)}")
        return

    if not timeline:
        st.warning(f"No clinical encounter graph records available for {selected_patient_id}.")
        return

    fig = build_patient_knowledge_graph(selected_patient_id, timeline, profile)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("ℹ️ Schema & Relationship Details"):
        st.markdown(
            """
            - **`HAD_VISIT`**: Connects Patient to each encounter (`Visit`).
            - **`ATTENDED_BY`**: Links encounter to attending physician (`Doctor`). Shared doctors connect multiple visits.
            - **`FOLLOWED_BY`**: Connects consecutive encounters chronologically.
            - **`DIAGNOSED_WITH`**: Links encounter to condition (`Diagnosis`). Stores `diagnosis_id` and clinical status.
            - **`PRESCRIBED`**: Links encounter to pharmaceutical agent (`Medication`). Stores `prescription_id`, dosage, and effectiveness.
            - **`HAD_TEST`**: Links encounter to individual laboratory observation (`LabTest`).
            """
        )
