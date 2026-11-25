"""Read-only Neo4j graph service built on top of src/graph/retrieval.py."""

from datetime import date, datetime
import threading
from typing import Any, Dict, List, Optional

from backend.schemas.models import (
    ConditionInfo,
    GraphEdge,
    GraphNode,
    GraphStats,
    KnowledgeGraphResponse,
    OverviewResponse,
    OverviewTotals,
    PatientDirectoryItem,
    PatientProfileResponse,
    RecentEncounter,
    SchemaNodeInfo,
    SchemaRelInfo,
    VisitsOverTimePoint,
)
from src.graph.connection import get_driver
from src.graph.retrieval import (
    get_followup_comparison,
    get_hospital_overview_stats,
    get_lab_trends,
    get_medication_outcomes,
    get_patient_profile,
    get_patient_timeline,
    serialize_neo4j_value,
)

_driver_lock = threading.Lock()
_shared_driver: Optional[Any] = None


def init_shared_driver() -> Optional[Any]:
    """Initializes a shared Neo4j driver if credentials are present and reachable."""
    global _shared_driver
    with _driver_lock:
        if _shared_driver is None:
            _shared_driver = get_driver()
        return _shared_driver


def close_shared_driver() -> None:
    """Closes the shared Neo4j driver cleanly on application shutdown."""
    global _shared_driver
    with _driver_lock:
        if _shared_driver is not None:
            try:
                _shared_driver.close()
            finally:
                _shared_driver = None


def get_neo4j_driver() -> Any:
    """FastAPI dependency returning a shared Neo4j driver instance."""
    return init_shared_driver()


def check_neo4j_connectivity(driver: Optional[Any] = None) -> bool:
    """Performs a lightweight read-only connectivity check against Neo4j."""
    try:
        active_driver = driver or get_neo4j_driver()
        with active_driver.session(default_access_mode="READ") as session:
            rec = session.run("RETURN 1 AS ping").single()
            return bool(rec and rec.get("ping") == 1)
    except Exception:
        return False


def compute_age(dob_str: Optional[str]) -> Optional[int]:
    """Derives integer age in years from ISO date of birth string."""
    if not dob_str:
        return None
    try:
        dob_d = datetime.fromisoformat(str(dob_str)).date()
        today_d = date.today()
        return today_d.year - dob_d.year - ((today_d.month, today_d.day) < (dob_d.month, dob_d.day))
    except Exception:
        return None


def _filter_monthly_points(points: List[VisitsOverTimePoint], time_range: str) -> List[VisitsOverTimePoint]:
    if not points or time_range == "all":
        return points
    if time_range == "2024":
        return [p for p in points if p.month.startswith("2024-")]
    if time_range == "2023":
        return [p for p in points if p.month.startswith("2023-")]
    if time_range == "6m":
        return points[-6:]
    if time_range == "12m":
        return points[-12:]
    return points


def get_overview_data(driver: Any, time_range: str = "all") -> OverviewResponse:
    """Combines baseline hospital stats with visit trends, recent encounters, and schema counts."""
    base_stats = get_hospital_overview_stats(driver=driver)
    raw_totals = base_stats.get("totals", {})

    clinical_records = (
        int(raw_totals.get("total_diagnosis_records", 0))
        + int(raw_totals.get("total_prescription_records", 0))
        + int(raw_totals.get("total_lab_records", 0))
    )

    totals = OverviewTotals(
        total_nodes=int(raw_totals.get("total_nodes", 0)),
        total_relationships=int(raw_totals.get("total_relationships", 0)),
        total_patients=int(raw_totals.get("total_patients", 0)),
        total_doctors=int(raw_totals.get("total_doctors", 0)),
        total_visits=int(raw_totals.get("total_visits", 0)),
        total_diagnosis_records=int(raw_totals.get("total_diagnosis_records", 0)),
        total_prescription_records=int(raw_totals.get("total_prescription_records", 0)),
        total_lab_records=int(raw_totals.get("total_lab_records", 0)),
        total_clinical_records=clinical_records,
    )

    with driver.session(default_access_mode="READ") as session:
        q_monthly = """
        MATCH (v:Visit)
        WITH substring(toString(v.visit_date), 0, 7) AS month, v.admission_type AS adm
        RETURN month,
               count(*) AS total_visits,
               sum(CASE WHEN adm = 'Follow-up' THEN 1 ELSE 0 END) AS follow_up,
               sum(CASE WHEN adm = 'Outpatient' THEN 1 ELSE 0 END) AS outpatient,
               sum(CASE WHEN adm = 'Inpatient' THEN 1 ELSE 0 END) AS inpatient,
               sum(CASE WHEN adm = 'Emergency' THEN 1 ELSE 0 END) AS emergency
        ORDER BY month ASC
        """
        monthly_rows = serialize_neo4j_value(session.run(q_monthly).data())

        q_recent = """
        MATCH (p:Patient)-[:HAD_VISIT]->(v:Visit)
        OPTIONAL MATCH (v)-[:ATTENDED_BY]->(doc:Doctor)
        OPTIONAL MATCH (v)-[:DIAGNOSED_WITH]->(d:Diagnosis)
        RETURN v.visit_id AS visit_id,
               toString(v.visit_date) AS visit_date,
               v.admission_type AS admission_type,
               p.patient_id AS patient_id,
               p.name AS patient_name,
               doc.doctor_id AS doctor_id,
               doc.name AS doctor_name,
               d.condition AS condition
        ORDER BY v.visit_date DESC, v.visit_id DESC
        LIMIT 8
        """
        recent_rows = serialize_neo4j_value(session.run(q_recent).data())

        q_schema_nodes = """
        MATCH (n)
        RETURN head(labels(n)) AS label, count(*) AS count
        ORDER BY count DESC, label ASC
        """
        schema_nodes_rows = serialize_neo4j_value(session.run(q_schema_nodes).data())

        q_schema_rels = """
        MATCH ()-[r]->()
        RETURN type(r) AS relationship_type, count(*) AS count
        ORDER BY count DESC, relationship_type ASC
        """
        schema_rels_rows = serialize_neo4j_value(session.run(q_schema_rels).data())

    monthly_points = [VisitsOverTimePoint(**row) for row in monthly_rows if row.get("month")]
    filtered_points = _filter_monthly_points(monthly_points, time_range)

    return OverviewResponse(
        time_range=time_range,
        totals=totals,
        conditions=base_stats.get("conditions", []),
        admission_types=base_stats.get("admission_types", []),
        visits_over_time=filtered_points,
        recent_encounters=[RecentEncounter(**r) for r in recent_rows],
        schema_nodes=[SchemaNodeInfo(**r) for r in schema_nodes_rows if r.get("label")],
        schema_relationships=[SchemaRelInfo(**r) for r in schema_rels_rows if r.get("relationship_type")],
    )


def get_patients_directory_enriched(
    driver: Any,
    search: Optional[str] = None,
    condition: Optional[str] = None,
    gender: Optional[str] = None,
    sort_by: str = "patient_id",
    sort_order: str = "asc",
) -> List[PatientDirectoryItem]:
    """Retrieves enriched patient directory records with visit counts, dates, and diagnosed conditions."""
    query = """
    MATCH (p:Patient)
    OPTIONAL MATCH (p)-[:HAD_VISIT]->(v:Visit)
    OPTIONAL MATCH (v)-[:DIAGNOSED_WITH]->(d:Diagnosis)
    WITH p,
         count(DISTINCT v) AS visit_count,
         min(v.visit_date) AS first_visit_date,
         max(v.visit_date) AS latest_visit_date,
         collect(DISTINCT d.condition) AS raw_conditions
    RETURN p.patient_id AS patient_id,
           p.name AS name,
           toString(p.dob) AS dob,
           p.gender AS gender,
           visit_count,
           toString(first_visit_date) AS first_visit_date,
           toString(latest_visit_date) AS latest_visit_date,
           [c IN raw_conditions WHERE c IS NOT NULL] AS conditions
    ORDER BY p.patient_id ASC
    """
    with driver.session(default_access_mode="READ") as session:
        rows = serialize_neo4j_value(session.run(query).data())

    items: List[PatientDirectoryItem] = []
    for row in rows:
        conds = sorted(row.get("conditions") or [])
        items.append(
            PatientDirectoryItem(
                patient_id=row["patient_id"],
                name=row["name"],
                dob=row.get("dob"),
                gender=row.get("gender"),
                age=compute_age(row.get("dob")),
                visit_count=int(row.get("visit_count", 0)),
                first_visit_date=row.get("first_visit_date"),
                latest_visit_date=row.get("latest_visit_date"),
                conditions=conds,
                primary_condition=conds[0] if conds else None,
            )
        )

    if search:
        term = search.strip().lower()
        items = [
            p
            for p in items
            if term in p.patient_id.lower()
            or term in p.name.lower()
            or any(term in c.lower() for c in p.conditions)
        ]

    if condition and condition.lower() != "all":
        cond_target = condition.strip().lower()
        items = [p for p in items if any(c.lower() == cond_target for c in p.conditions)]

    if gender and gender.lower() != "all":
        gen_target = gender.strip().lower()
        items = [p for p in items if (p.gender or "").lower() == gen_target]

    reverse = sort_order.lower() == "desc"
    if sort_by == "name":
        items.sort(key=lambda p: p.name.lower(), reverse=reverse)
    elif sort_by == "visit_count":
        items.sort(key=lambda p: (p.visit_count, p.patient_id), reverse=reverse)
    elif sort_by == "latest_visit_date":
        items.sort(key=lambda p: (p.latest_visit_date or "", p.patient_id), reverse=reverse)
    elif sort_by == "age":
        items.sort(key=lambda p: (p.age if p.age is not None else -1, p.patient_id), reverse=reverse)
    else:
        items.sort(key=lambda p: p.patient_id, reverse=reverse)

    return items


def get_patient_profile_enriched(driver: Any, patient_id: str) -> Optional[PatientProfileResponse]:
    """Retrieves a patient's profile enriched with derived age, conditions, and attending doctors."""
    profile = get_patient_profile(patient_id, driver=driver)
    if not profile:
        return None

    timeline = get_patient_timeline(patient_id, driver=driver)
    conditions = sorted(
        {
            dx["condition"]
            for visit in timeline
            for dx in visit.get("diagnoses", [])
            if dx.get("condition")
        }
    )
    doctors = sorted(
        {
            visit["doctor"]["name"]
            for visit in timeline
            if isinstance(visit.get("doctor"), dict) and visit["doctor"].get("name")
        }
    )

    return PatientProfileResponse(
        patient_id=profile["patient_id"],
        name=profile["name"],
        dob=profile.get("dob"),
        gender=profile.get("gender"),
        age=compute_age(profile.get("dob")),
        visit_count=int(profile.get("visit_count", 0)),
        first_visit_date=profile.get("first_visit_date"),
        latest_visit_date=profile.get("latest_visit_date"),
        conditions=conditions,
        attending_doctors=doctors,
    )


def _node_id(node_type: str, entity_id: str) -> str:
    return f"{node_type}:{entity_id}"


def _build_graph_stats(nodes: List[GraphNode], edges: List[GraphEdge]) -> GraphStats:
    node_counts: Dict[str, int] = {}
    for node in nodes:
        node_counts[node.type] = node_counts.get(node.type, 0) + 1

    edge_counts: Dict[str, int] = {}
    for edge in edges:
        edge_counts[edge.type] = edge_counts.get(edge.type, 0) + 1

    return GraphStats(
        node_count=len(nodes),
        edge_count=len(edges),
        node_counts_by_type=node_counts,
        edge_counts_by_type=edge_counts,
    )


def build_patient_subgraph(
    patient_id: str,
    profile: Dict[str, Any],
    timeline: List[Dict[str, Any]],
) -> KnowledgeGraphResponse:
    """
    Constructs a Cytoscape-ready knowledge graph subgraph for one patient.
    Deduplicates shared Doctor, Diagnosis, and Medication entities while preserving
    relationship directions and clinical record properties.
    """
    nodes_map: Dict[str, GraphNode] = {}
    edges_map: Dict[str, GraphEdge] = {}

    p_node_id = _node_id("Patient", patient_id)
    nodes_map[p_node_id] = GraphNode(
        id=p_node_id,
        entity_id=patient_id,
        type="Patient",
        label=profile.get("name", patient_id),
        subtitle=patient_id,
        properties={
            "patient_id": patient_id,
            "name": profile.get("name"),
            "dob": profile.get("dob"),
            "gender": profile.get("gender"),
            "age": compute_age(profile.get("dob")),
            "visit_count": profile.get("visit_count", len(timeline)),
        },
    )

    for idx, visit in enumerate(timeline):
        vid = visit["visit_id"]
        v_node_id = _node_id("Visit", vid)
        v_date = visit.get("visit_date", "")
        adm = visit.get("admission_type", "")

        nodes_map[v_node_id] = GraphNode(
            id=v_node_id,
            entity_id=vid,
            type="Visit",
            label=vid,
            subtitle=f"{v_date} • {adm}",
            properties={
                "visit_id": vid,
                "visit_date": v_date,
                "admission_type": adm,
                "patient_id": patient_id,
            },
        )

        had_visit_id = f"HAD_VISIT:{p_node_id}->{v_node_id}"
        edges_map[had_visit_id] = GraphEdge(
            id=had_visit_id,
            source=p_node_id,
            target=v_node_id,
            type="HAD_VISIT",
            label="HAD_VISIT",
            properties={"patient_id": patient_id, "visit_id": vid},
        )

        if idx > 0:
            prev_vid = timeline[idx - 1]["visit_id"]
            prev_node_id = _node_id("Visit", prev_vid)
            followed_id = f"FOLLOWED_BY:{prev_node_id}->{v_node_id}"
            edges_map[followed_id] = GraphEdge(
                id=followed_id,
                source=prev_node_id,
                target=v_node_id,
                type="FOLLOWED_BY",
                label="FOLLOWED_BY",
                properties={"from_visit": prev_vid, "to_visit": vid},
            )

        doc = visit.get("doctor") if isinstance(visit.get("doctor"), dict) else {}
        doc_id = doc.get("doctor_id")
        if doc_id:
            d_node_id = _node_id("Doctor", doc_id)
            if d_node_id not in nodes_map:
                nodes_map[d_node_id] = GraphNode(
                    id=d_node_id,
                    entity_id=doc_id,
                    type="Doctor",
                    label=doc.get("name") or doc_id,
                    subtitle=doc.get("specialty") or doc_id,
                    properties={
                        "doctor_id": doc_id,
                        "name": doc.get("name"),
                        "specialty": doc.get("specialty"),
                    },
                )
            att_id = f"ATTENDED_BY:{v_node_id}->{d_node_id}"
            edges_map[att_id] = GraphEdge(
                id=att_id,
                source=v_node_id,
                target=d_node_id,
                type="ATTENDED_BY",
                label="ATTENDED_BY",
                properties={"visit_id": vid, "doctor_id": doc_id},
            )

        for dx in visit.get("diagnoses", []):
            cond = dx.get("condition")
            if not cond:
                continue
            dx_node_id = _node_id("Diagnosis", cond)
            if dx_node_id not in nodes_map:
                nodes_map[dx_node_id] = GraphNode(
                    id=dx_node_id,
                    entity_id=cond,
                    type="Diagnosis",
                    label=cond,
                    subtitle="Shared Condition",
                    properties={"condition": cond},
                )
            diag_id = dx.get("diagnosis_id") or f"{vid}:{cond}"
            rel_id = f"DIAGNOSED_WITH:{v_node_id}->{dx_node_id}:{diag_id}"
            edges_map[rel_id] = GraphEdge(
                id=rel_id,
                source=v_node_id,
                target=dx_node_id,
                type="DIAGNOSED_WITH",
                label="DIAGNOSED_WITH",
                properties={
                    "diagnosis_id": dx.get("diagnosis_id"),
                    "status": dx.get("status"),
                    "visit_id": vid,
                    "condition": cond,
                },
            )

        for rx in visit.get("medications", []):
            med_name = rx.get("medication_name")
            if not med_name:
                continue
            m_node_id = _node_id("Medication", med_name)
            if m_node_id not in nodes_map:
                nodes_map[m_node_id] = GraphNode(
                    id=m_node_id,
                    entity_id=med_name,
                    type="Medication",
                    label=med_name,
                    subtitle="Shared Medication",
                    properties={"name": med_name},
                )
            rx_id = rx.get("prescription_id") or f"{vid}:{med_name}"
            rel_id = f"PRESCRIBED:{v_node_id}->{m_node_id}:{rx_id}"
            edges_map[rel_id] = GraphEdge(
                id=rel_id,
                source=v_node_id,
                target=m_node_id,
                type="PRESCRIBED",
                label="PRESCRIBED",
                properties={
                    "prescription_id": rx.get("prescription_id"),
                    "dosage": rx.get("dosage"),
                    "is_effective": rx.get("is_effective"),
                    "visit_id": vid,
                    "medication_name": med_name,
                },
            )

        for lab in visit.get("lab_tests", []):
            tid = lab.get("test_id")
            if not tid:
                continue
            t_node_id = _node_id("LabTest", tid)
            t_name = lab.get("test_name", "Lab Test")
            t_val = lab.get("value")
            t_unit = lab.get("unit", "")
            nodes_map[t_node_id] = GraphNode(
                id=t_node_id,
                entity_id=tid,
                type="LabTest",
                label=f"{t_name}: {t_val} {t_unit}".strip(),
                subtitle=tid,
                properties={
                    "test_id": tid,
                    "test_name": t_name,
                    "value": t_val,
                    "unit": t_unit,
                    "visit_id": vid,
                },
            )
            rel_id = f"HAD_TEST:{v_node_id}->{t_node_id}"
            edges_map[rel_id] = GraphEdge(
                id=rel_id,
                source=v_node_id,
                target=t_node_id,
                type="HAD_TEST",
                label="HAD_TEST",
                properties={"visit_id": vid, "test_id": tid},
            )

    nodes = list(nodes_map.values())
    edges = list(edges_map.values())
    return KnowledgeGraphResponse(
        scope="patient",
        patient_id=patient_id,
        nodes=nodes,
        edges=edges,
        stats=_build_graph_stats(nodes, edges),
    )


def get_patient_graph(driver: Any, patient_id: str) -> Optional[KnowledgeGraphResponse]:
    """Fetches profile and timeline for a patient and returns a deduplicated knowledge graph."""
    profile = get_patient_profile(patient_id, driver=driver)
    if not profile:
        return None
    timeline = get_patient_timeline(patient_id, driver=driver)
    return build_patient_subgraph(patient_id, profile, timeline)


def get_cohort_graph(
    driver: Any,
    condition: Optional[str] = None,
    limit_patients: int = 8,
) -> KnowledgeGraphResponse:
    """
    Constructs a multi-patient cohort subgraph showing shared Doctors, Diagnoses,
    and Medications across patients.
    """
    patients = get_patients_directory_enriched(
        driver=driver,
        condition=condition,
        sort_by="patient_id",
        sort_order="asc",
    )[:limit_patients]

    nodes_map: Dict[str, GraphNode] = {}
    edges_map: Dict[str, GraphEdge] = {}

    for p in patients:
        pid = p.patient_id
        profile = p.model_dump()
        timeline = get_patient_timeline(pid, driver=driver)
        sub = build_patient_subgraph(pid, profile, timeline)
        for node in sub.nodes:
            if node.id not in nodes_map:
                nodes_map[node.id] = node
        for edge in sub.edges:
            if edge.id not in edges_map:
                edges_map[edge.id] = edge

    nodes = list(nodes_map.values())
    edges = list(edges_map.values())
    return KnowledgeGraphResponse(
        scope="cohort",
        condition=condition,
        nodes=nodes,
        edges=edges,
        stats=_build_graph_stats(nodes, edges),
    )


def get_conditions_summary(driver: Any) -> List[ConditionInfo]:
    """Retrieves condition metadata including patient counts, records, and primary biomarker."""
    query = """
    MATCH (p:Patient)-[:HAD_VISIT]->(v:Visit)-[:DIAGNOSED_WITH]->(d:Diagnosis)
    OPTIONAL MATCH (v)-[:HAD_TEST]->(t:LabTest)
    WITH d.condition AS condition,
         count(DISTINCT p) AS patient_count,
         count(DISTINCT v) AS record_count,
         head(collect(DISTINCT t.test_name)) AS biomarker,
         head(collect(DISTINCT t.unit)) AS unit
    RETURN condition, patient_count, record_count, biomarker, unit
    ORDER BY patient_count DESC, condition ASC
    """
    with driver.session(default_access_mode="READ") as session:
        rows = serialize_neo4j_value(session.run(query).data())
    return [ConditionInfo(**row) for row in rows]
