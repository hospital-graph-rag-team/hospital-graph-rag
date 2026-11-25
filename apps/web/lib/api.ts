import type {
  ChatResponse,
  ConditionsResponse,
  HealthStatus,
  KnowledgeGraphResponse,
  MedicationAnalyticsResponse,
  OverviewResponse,
  PatientFollowupsResponse,
  PatientLabTrendsResponse,
  PatientListResponse,
  PatientProfile,
  PatientTimelineResponse,
} from "@/types/clinical";

export class ApiClientError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
  }
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg =
      typeof data?.detail === "string"
        ? data.detail
        : `Request failed with status ${res.status}`;
    throw new ApiClientError(msg, res.status);
  }
  return data as T;
}

export const apiClient = {
  getHealth: () => fetchJson<HealthStatus>("/api/health"),

  getOverview: (timeRange: string = "all") =>
    fetchJson<OverviewResponse>(
      `/api/overview?time_range=${encodeURIComponent(timeRange)}`
    ),

  getPatients: (params?: {
    search?: string;
    condition?: string;
    gender?: string;
    sort_by?: string;
    sort_order?: string;
  }) => {
    const sp = new URLSearchParams();
    if (params?.search) sp.set("search", params.search);
    if (params?.condition && params.condition !== "all")
      sp.set("condition", params.condition);
    if (params?.gender && params.gender !== "all")
      sp.set("gender", params.gender);
    if (params?.sort_by) sp.set("sort_by", params.sort_by);
    if (params?.sort_order) sp.set("sort_order", params.sort_order);
    const qs = sp.toString();
    return fetchJson<PatientListResponse>(`/api/patients${qs ? `?${qs}` : ""}`);
  },

  getPatientProfile: (patientId: string, signal?: AbortSignal) =>
    fetchJson<PatientProfile>(
      `/api/patients/${encodeURIComponent(patientId)}`,
      { signal }
    ),

  getPatientTimeline: (patientId: string, signal?: AbortSignal) =>
    fetchJson<PatientTimelineResponse>(
      `/api/patients/${encodeURIComponent(patientId)}/timeline`,
      { signal }
    ),

  getPatientLabTrends: (
    patientId: string,
    testName?: string,
    signal?: AbortSignal
  ) => {
    const qs = testName ? `?test_name=${encodeURIComponent(testName)}` : "";
    return fetchJson<PatientLabTrendsResponse>(
      `/api/patients/${encodeURIComponent(patientId)}/lab-trends${qs}`,
      { signal }
    );
  },

  getPatientFollowups: (patientId: string, signal?: AbortSignal) =>
    fetchJson<PatientFollowupsResponse>(
      `/api/patients/${encodeURIComponent(patientId)}/followups`,
      { signal }
    ),

  getPatientGraph: (patientId: string, signal?: AbortSignal) =>
    fetchJson<KnowledgeGraphResponse>(
      `/api/patients/${encodeURIComponent(patientId)}/graph`,
      { signal }
    ),

  getCohortGraph: (
    condition?: string,
    limit: number = 6,
    signal?: AbortSignal
  ) => {
    const sp = new URLSearchParams({ limit: String(limit) });
    if (condition && condition !== "all") sp.set("condition", condition);
    return fetchJson<KnowledgeGraphResponse>(
      `/api/graph/cohort?${sp.toString()}`,
      { signal }
    );
  },

  getConditions: () => fetchJson<ConditionsResponse>("/api/conditions"),

  getMedicationAnalytics: (condition: string) =>
    fetchJson<MedicationAnalyticsResponse>(
      `/api/analytics/medications?condition=${encodeURIComponent(condition)}`
    ),

  sendChatQuery: (
    payload: {
      query: string;
      selected_patient_id?: string | null;
      conversation_history?: Array<{ role: "user" | "assistant"; content: string }>;
    },
    signal?: AbortSignal
  ) =>
    fetchJson<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify(payload),
      signal,
    }),

  checkDemoAccess: () =>
    fetchJson<{ required: boolean; unlocked: boolean }>("/api/demo-access"),

  unlockDemoAccess: (code: string) =>
    fetchJson<{ unlocked: boolean }>("/api/demo-access", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
};
