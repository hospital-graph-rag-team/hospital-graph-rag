export interface HealthStatus {
  status: "ok" | "degraded";
  service: string;
  version: string;
  environment: string;
  neo4j_connected: boolean;
  groq_configured: boolean;
  model_name: string;
  auth_enabled: boolean;
  timestamp: string;
}

export interface OverviewTotals {
  total_nodes: number;
  total_relationships: number;
  total_patients: number;
  total_doctors: number;
  total_visits: number;
  total_diagnosis_records: number;
  total_prescription_records: number;
  total_lab_records: number;
  total_clinical_records: number;
}

export interface ConditionStat {
  condition: string;
  patient_count: number;
  record_count: number;
}

export interface AdmissionTypeStat {
  admission_type: string;
  count: number;
}

export interface VisitsOverTimePoint {
  month: string;
  total_visits: number;
  follow_up: number;
  outpatient: number;
  inpatient: number;
  emergency: number;
}

export interface RecentEncounter {
  visit_id: string;
  visit_date: string;
  admission_type: string;
  patient_id: string;
  patient_name: string;
  doctor_id?: string | null;
  doctor_name?: string | null;
  condition?: string | null;
}

export interface SchemaNodeInfo {
  label: string;
  count: number;
}

export interface SchemaRelInfo {
  relationship_type: string;
  count: number;
}

export interface OverviewResponse {
  time_range: string;
  totals: OverviewTotals;
  conditions: ConditionStat[];
  admission_types: AdmissionTypeStat[];
  visits_over_time: VisitsOverTimePoint[];
  recent_encounters: RecentEncounter[];
  schema_nodes: SchemaNodeInfo[];
  schema_relationships: SchemaRelInfo[];
}

export interface PatientDirectoryItem {
  patient_id: string;
  name: string;
  dob?: string | null;
  gender?: string | null;
  age?: number | null;
  visit_count: number;
  first_visit_date?: string | null;
  latest_visit_date?: string | null;
  conditions: string[];
  primary_condition?: string | null;
}

export interface PatientListResponse {
  total: number;
  patients: PatientDirectoryItem[];
}

export interface PatientProfile {
  patient_id: string;
  name: string;
  dob?: string | null;
  gender?: string | null;
  age?: number | null;
  visit_count: number;
  first_visit_date?: string | null;
  latest_visit_date?: string | null;
  conditions: string[];
  attending_doctors: string[];
}

export interface DoctorInfo {
  doctor_id?: string | null;
  name?: string | null;
  specialty?: string | null;
}

export interface DiagnosisRecord {
  diagnosis_id?: string | null;
  condition: string;
  status?: string | null;
}

export interface MedicationRecord {
  prescription_id?: string | null;
  medication_name: string;
  dosage?: string | null;
  is_effective?: boolean | null;
}

export interface LabTestRecord {
  test_id: string;
  test_name: string;
  value: number;
  unit: string;
}

export interface VisitRecord {
  visit_id: string;
  visit_date: string;
  admission_type: string;
  doctor?: DoctorInfo | null;
  diagnoses: DiagnosisRecord[];
  medications: MedicationRecord[];
  lab_tests: LabTestRecord[];
}

export interface PatientTimelineResponse {
  patient_id: string;
  visit_count: number;
  visits: VisitRecord[];
}

export interface LabObservation {
  visit_id: string;
  visit_date: string;
  test_id: string;
  value: number;
  unit: string;
}

export interface LabTrendGroup {
  patient_id: string;
  biomarker: string;
  unit: string;
  observation_count: number;
  initial_value: number;
  latest_value: number;
  absolute_change: number;
  percentage_change?: number | null;
  direction: string;
  observations: LabObservation[];
}

export interface PatientLabTrendsResponse {
  patient_id: string;
  trends: LabTrendGroup[];
}

export interface FollowupVisitSummary {
  visit_id: string;
  visit_date: string;
  admission_type?: string | null;
  doctor?: string | null;
  diagnoses: DiagnosisRecord[];
  prescriptions: MedicationRecord[];
}

export interface FollowupLabComparison {
  biomarker: string;
  unit: string;
  v1_test_id: string;
  v1_value: number;
  v2_test_id: string;
  v2_value: number;
  absolute_change: number;
  percentage_change?: number | null;
  direction: string;
}

export interface FollowupComparisonItem {
  patient_id: string;
  previous_visit: FollowupVisitSummary;
  followup_visit: FollowupVisitSummary;
  days_between: number;
  lab_comparisons: FollowupLabComparison[];
}

export interface PatientFollowupsResponse {
  patient_id: string;
  transition_count: number;
  followups: FollowupComparisonItem[];
}

export type NodeType =
  | "Patient"
  | "Visit"
  | "Doctor"
  | "Diagnosis"
  | "Medication"
  | "LabTest";

export type EdgeType =
  | "HAD_VISIT"
  | "ATTENDED_BY"
  | "DIAGNOSED_WITH"
  | "PRESCRIBED"
  | "HAD_TEST"
  | "FOLLOWED_BY";

export interface GraphNode {
  id: string;
  entity_id: string;
  type: NodeType;
  label: string;
  subtitle?: string | null;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: EdgeType;
  label: string;
  properties: Record<string, unknown>;
}

export interface GraphStats {
  node_count: number;
  edge_count: number;
  node_counts_by_type: Record<string, number>;
  edge_counts_by_type: Record<string, number>;
}

export interface KnowledgeGraphResponse {
  scope: "patient" | "cohort";
  patient_id?: string | null;
  condition?: string | null;
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: GraphStats;
}

export interface ConditionInfo {
  condition: string;
  patient_count: number;
  record_count: number;
  biomarker?: string | null;
  unit?: string | null;
}

export interface ConditionsResponse {
  conditions: ConditionInfo[];
}

export interface MedicationEvidenceItem {
  patient_id: string;
  v1_id: string;
  v2_id: string;
  v1_value: number;
  v2_value: number;
  delta: number;
  direction: string;
  prescription_id: string;
}

export interface MedicationOutcomeItem {
  medication: string;
  biomarker: string;
  unit: string;
  unique_patient_count: number;
  eligible_transitions: number;
  improved_transitions: number;
  worsened_transitions: number;
  unchanged_transitions: number;
  betterment_rate_pct: number;
  evidence_sample: MedicationEvidenceItem[];
}

export interface MedicationAnalyticsResponse {
  condition: string;
  biomarker?: string | null;
  unit?: string | null;
  total_eligible_transitions: number;
  total_unique_patients: number;
  medications: MedicationOutcomeItem[];
  disclaimer: string;
}

export interface ToolCallItem {
  tool: string;
  arguments: Record<string, unknown>;
  summary: string;
}

export interface CitationValidationResult {
  supported: string[];
  unsupported: string[];
  is_valid: boolean;
}

export interface RetrievedEvidenceItem {
  tool: string;
  data: unknown;
}

export interface ChatResponse {
  query: string;
  patient_id?: string | null;
  status: string;
  answer: string;
  citations: string[];
  citation_validation: CitationValidationResult;
  tool_calls: ToolCallItem[];
  retrieved_evidence: RetrievedEvidenceItem[];
  error?: string | null;
  model_name: string;
}

export interface ChatThreadMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  response?: ChatResponse;
  isError?: boolean;
}
