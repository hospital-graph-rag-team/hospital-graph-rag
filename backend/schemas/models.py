"""Typed Pydantic request and response schemas for ClinicalGraph 2.0 API endpoints."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str = "ClinicalGraph API"
    version: str = "2.0.0"
    environment: str
    neo4j_connected: bool
    groq_configured: bool
    model_name: str
    auth_enabled: bool
    timestamp: str


class OverviewTotals(BaseModel):
    total_nodes: int = 0
    total_relationships: int = 0
    total_patients: int = 0
    total_doctors: int = 0
    total_visits: int = 0
    total_diagnosis_records: int = 0
    total_prescription_records: int = 0
    total_lab_records: int = 0
    total_clinical_records: int = 0


class ConditionStat(BaseModel):
    condition: str
    patient_count: int
    record_count: int


class AdmissionTypeStat(BaseModel):
    admission_type: str
    count: int


class VisitsOverTimePoint(BaseModel):
    month: str
    total_visits: int
    follow_up: int = 0
    outpatient: int = 0
    inpatient: int = 0
    emergency: int = 0


class RecentEncounter(BaseModel):
    visit_id: str
    visit_date: str
    admission_type: str
    patient_id: str
    patient_name: str
    doctor_id: Optional[str] = None
    doctor_name: Optional[str] = None
    condition: Optional[str] = None


class SchemaNodeInfo(BaseModel):
    label: str
    count: int


class SchemaRelInfo(BaseModel):
    relationship_type: str
    count: int


class OverviewResponse(BaseModel):
    time_range: str = "all"
    totals: OverviewTotals
    conditions: List[ConditionStat]
    admission_types: List[AdmissionTypeStat]
    visits_over_time: List[VisitsOverTimePoint]
    recent_encounters: List[RecentEncounter]
    schema_nodes: List[SchemaNodeInfo]
    schema_relationships: List[SchemaRelInfo]


class PatientDirectoryItem(BaseModel):
    patient_id: str
    name: str
    dob: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    visit_count: int = 0
    first_visit_date: Optional[str] = None
    latest_visit_date: Optional[str] = None
    conditions: List[str] = Field(default_factory=list)
    primary_condition: Optional[str] = None


class PatientListResponse(BaseModel):
    total: int
    patients: List[PatientDirectoryItem]


class PatientProfileResponse(BaseModel):
    patient_id: str
    name: str
    dob: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    visit_count: int = 0
    first_visit_date: Optional[str] = None
    latest_visit_date: Optional[str] = None
    conditions: List[str] = Field(default_factory=list)
    attending_doctors: List[str] = Field(default_factory=list)


class DoctorInfo(BaseModel):
    doctor_id: Optional[str] = None
    name: Optional[str] = None
    specialty: Optional[str] = None


class DiagnosisRecord(BaseModel):
    diagnosis_id: Optional[str] = None
    condition: str
    status: Optional[str] = None


class MedicationRecord(BaseModel):
    prescription_id: Optional[str] = None
    medication_name: str
    dosage: Optional[str] = None
    is_effective: Optional[bool] = None


class LabTestRecord(BaseModel):
    test_id: str
    test_name: str
    value: float
    unit: str


class VisitRecord(BaseModel):
    visit_id: str
    visit_date: str
    admission_type: str
    doctor: Optional[DoctorInfo] = None
    diagnoses: List[DiagnosisRecord] = Field(default_factory=list)
    medications: List[MedicationRecord] = Field(default_factory=list)
    lab_tests: List[LabTestRecord] = Field(default_factory=list)


class PatientTimelineResponse(BaseModel):
    patient_id: str
    visit_count: int
    visits: List[VisitRecord]


class LabObservation(BaseModel):
    visit_id: str
    visit_date: str
    test_id: str
    value: float
    unit: str


class LabTrendGroup(BaseModel):
    patient_id: str
    biomarker: str
    unit: str
    observation_count: int
    initial_value: float
    latest_value: float
    absolute_change: float
    percentage_change: Optional[float] = None
    direction: str
    observations: List[LabObservation]


class PatientLabTrendsResponse(BaseModel):
    patient_id: str
    trends: List[LabTrendGroup]


class FollowupVisitSummary(BaseModel):
    visit_id: str
    visit_date: str
    admission_type: Optional[str] = None
    doctor: Optional[str] = None
    diagnoses: List[DiagnosisRecord] = Field(default_factory=list)
    prescriptions: List[MedicationRecord] = Field(default_factory=list)


class FollowupLabComparison(BaseModel):
    biomarker: str
    unit: str
    v1_test_id: str
    v1_value: float
    v2_test_id: str
    v2_value: float
    absolute_change: float
    percentage_change: Optional[float] = None
    direction: str


class FollowupComparisonItem(BaseModel):
    patient_id: str
    previous_visit: FollowupVisitSummary
    followup_visit: FollowupVisitSummary
    days_between: int
    lab_comparisons: List[FollowupLabComparison]


class PatientFollowupsResponse(BaseModel):
    patient_id: str
    transition_count: int
    followups: List[FollowupComparisonItem]


NodeType = Literal["Patient", "Visit", "Doctor", "Diagnosis", "Medication", "LabTest"]
EdgeType = Literal[
    "HAD_VISIT",
    "ATTENDED_BY",
    "DIAGNOSED_WITH",
    "PRESCRIBED",
    "HAD_TEST",
    "FOLLOWED_BY",
]


class GraphNode(BaseModel):
    id: str
    entity_id: str
    type: NodeType
    label: str
    subtitle: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: EdgeType
    label: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphStats(BaseModel):
    node_count: int
    edge_count: int
    node_counts_by_type: Dict[str, int]
    edge_counts_by_type: Dict[str, int]


class KnowledgeGraphResponse(BaseModel):
    scope: Literal["patient", "cohort"]
    patient_id: Optional[str] = None
    condition: Optional[str] = None
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    stats: GraphStats


class ConditionInfo(BaseModel):
    condition: str
    patient_count: int
    record_count: int
    biomarker: Optional[str] = None
    unit: Optional[str] = None


class ConditionsResponse(BaseModel):
    conditions: List[ConditionInfo]


class MedicationEvidenceItem(BaseModel):
    patient_id: str
    v1_id: str
    v2_id: str
    v1_value: float
    v2_value: float
    delta: float
    direction: str
    prescription_id: str


class MedicationOutcomeItem(BaseModel):
    medication: str
    biomarker: str
    unit: str
    unique_patient_count: int
    eligible_transitions: int
    improved_transitions: int
    worsened_transitions: int
    unchanged_transitions: int
    betterment_rate_pct: float
    evidence_sample: List[MedicationEvidenceItem]


class MedicationAnalyticsResponse(BaseModel):
    condition: str
    biomarker: Optional[str] = None
    unit: Optional[str] = None
    total_eligible_transitions: int
    total_unique_patients: int
    medications: List[MedicationOutcomeItem]
    disclaimer: str


class ChatMessageInput(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1500)
    selected_patient_id: Optional[str] = Field(default=None, max_length=16)
    conversation_history: List[ChatMessageInput] = Field(default_factory=list, max_length=12)


class ToolCallItem(BaseModel):
    tool: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    summary: str


class CitationValidationResult(BaseModel):
    supported: List[str] = Field(default_factory=list)
    unsupported: List[str] = Field(default_factory=list)
    is_valid: bool = True


class RetrievedEvidenceItem(BaseModel):
    tool: str
    data: Any


class ChatResponse(BaseModel):
    query: str
    patient_id: Optional[str] = None
    status: str
    answer: str
    citations: List[str] = Field(default_factory=list)
    citation_validation: CitationValidationResult
    tool_calls: List[ToolCallItem] = Field(default_factory=list)
    retrieved_evidence: List[RetrievedEvidenceItem] = Field(default_factory=list)
    error: Optional[str] = None
    model_name: str
