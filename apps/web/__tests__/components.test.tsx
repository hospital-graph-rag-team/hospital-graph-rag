import React from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { LabTrendsPanel } from "@/components/patients/lab-trends-panel";
import { FollowupComparisonPanel } from "@/components/patients/followup-panel";
import { MedicationAnalyticsView } from "@/components/analytics/medication-analytics";
import { AiAssistantView } from "@/components/assistant/ai-assistant";
import {
  citationCategory,
  formatDateShort,
  isPatientCitation,
  isVisitCitation,
} from "@/lib/utils";
import type { FollowupComparisonItem, LabTrendGroup } from "@/types/clinical";

const mockOpenPatient = vi.fn();
const mockOpenGraph = vi.fn();
const mockSetSelectedPatientId = vi.fn();

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/",
}));

vi.mock("@/components/providers/clinical-provider", () => ({
  useClinical: () => ({
    theme: "dark",
    toggleTheme: vi.fn(),
    sidebarCollapsed: false,
    setSidebarCollapsed: vi.fn(),
    selectedPatientId: "P101",
    setSelectedPatientId: mockSetSelectedPatientId,
    selectedPatient: {
      patient_id: "P101",
      name: "James Jones",
      visit_count: 3,
      conditions: ["Hyperlipidemia"],
    },
    patients: [
      {
        patient_id: "P101",
        name: "James Jones",
        visit_count: 3,
        conditions: ["Hyperlipidemia"],
      },
    ],
    patientsLoading: false,
    health: null,
    refreshHealth: vi.fn(),
    refreshPatients: vi.fn(),
    openPatient: mockOpenPatient,
    openGraph: mockOpenGraph,
    askAssistant: vi.fn(),
    openAnalytics: vi.fn(),
    demoGateRequired: false,
    demoUnlocked: true,
    demoChecked: true,
    unlockDemo: vi.fn(),
  }),
}));

vi.mock("@/lib/api", () => ({
  apiClient: {
    getConditions: vi.fn().mockResolvedValue({
      conditions: [
        {
          condition: "Type 2 Diabetes",
          patient_count: 15,
          record_count: 45,
          biomarker: "HbA1c",
          unit: "%",
        },
      ],
    }),
    getMedicationAnalytics: vi.fn().mockResolvedValue({
      condition: "Type 2 Diabetes",
      biomarker: "HbA1c",
      unit: "%",
      total_eligible_transitions: 30,
      total_unique_patients: 15,
      medications: [
        {
          medication: "Metformin",
          biomarker: "HbA1c",
          unit: "%",
          unique_patient_count: 6,
          eligible_transitions: 12,
          improved_transitions: 10,
          worsened_transitions: 2,
          unchanged_transitions: 0,
          betterment_rate_pct: 83.33,
          evidence_sample: [
            {
              patient_id: "P102",
              v1_id: "V304",
              v2_id: "V305",
              v1_value: 8.1,
              v2_value: 7.2,
              delta: -0.9,
              direction: "improved",
              prescription_id: "RX0004",
            },
          ],
        },
      ],
      disclaimer:
        "Synthetic observational outcomes based on consecutive visit transitions.",
    }),
    sendChatQuery: vi.fn().mockResolvedValue({
      query: "Summarize P101",
      patient_id: "P101",
      status: "success",
      answer: "Patient P101 visited on V301.",
      citations: ["P101", "V301", "V999"],
      citation_validation: {
        supported: ["P101", "V301"],
        unsupported: ["V999"],
        is_valid: false,
      },
      tool_calls: [
        {
          tool: "get_patient_timeline",
          arguments: { patient_id: "P101" },
          summary: "Retrieved 3 visits",
        },
      ],
      retrieved_evidence: [{ tool: "get_patient_timeline", data: [] }],
      error: null,
      model_name: "openai/gpt-oss-120b",
    }),
  },
}));

vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container" style={{ width: 600, height: 260 }}>
        {children}
      </div>
    ),
  };
});

describe("Clinical utility helpers", () => {
  it("categorizes and identifies patient and visit citations", () => {
    expect(isPatientCitation("P101")).toBe(true);
    expect(isPatientCitation("V301")).toBe(false);
    expect(isVisitCitation("V301")).toBe(true);
    expect(citationCategory("RX0001")).toBe("Prescription");
    expect(citationCategory("T0004")).toBe("LabTest");
    expect(formatDateShort("2024-08-18")).toContain("2024");
  });
});

describe("LabTrendsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders empty state when no lab trends exist", () => {
    render(<LabTrendsPanel trends={[]} />);
    expect(
      screen.getByText(/No laboratory measurements recorded/i)
    ).toBeInTheDocument();
  });

  it("handles single observation and zero-denominator percentage safely", () => {
    const singleTrend: LabTrendGroup[] = [
      {
        patient_id: "P101",
        biomarker: "HbA1c",
        unit: "%",
        observation_count: 1,
        initial_value: 7.4,
        latest_value: 7.4,
        absolute_change: 0,
        percentage_change: null,
        direction: "insufficient_data",
        observations: [
          {
            visit_id: "V301",
            visit_date: "2023-08-28",
            test_id: "T0001",
            value: 7.4,
            unit: "%",
          },
        ],
      },
    ];
    render(<LabTrendsPanel trends={singleTrend} />);
    expect(screen.getByText(/Only a single observation/i)).toBeInTheDocument();
    expect(screen.getByText("Single")).toBeInTheDocument();
  });

  it("allows switching between multiple biomarkers", () => {
    const trends: LabTrendGroup[] = [
      {
        patient_id: "P101",
        biomarker: "LDL Cholesterol",
        unit: "mg/dL",
        observation_count: 2,
        initial_value: 183.1,
        latest_value: 113.8,
        absolute_change: -69.3,
        percentage_change: -37.85,
        direction: "decreased",
        observations: [
          {
            visit_id: "V301",
            visit_date: "2023-08-28",
            test_id: "T0001",
            value: 183.1,
            unit: "mg/dL",
          },
          {
            visit_id: "V303",
            visit_date: "2023-10-18",
            test_id: "T0003",
            value: 113.8,
            unit: "mg/dL",
          },
        ],
      },
      {
        patient_id: "P101",
        biomarker: "Systolic BP",
        unit: "mmHg",
        observation_count: 2,
        initial_value: 148,
        latest_value: 132,
        absolute_change: -16,
        percentage_change: -10.81,
        direction: "decreased",
        observations: [
          {
            visit_id: "V301",
            visit_date: "2023-08-28",
            test_id: "T0010",
            value: 148,
            unit: "mmHg",
          },
          {
            visit_id: "V303",
            visit_date: "2023-10-18",
            test_id: "T0011",
            value: 132,
            unit: "mmHg",
          },
        ],
      },
    ];

    render(<LabTrendsPanel trends={trends} />);
    expect(screen.getByText(/LDL Cholesterol Trajectory/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Systolic BP/i }));
    expect(screen.getByText(/Systolic BP Trajectory/i)).toBeInTheDocument();
  });
});

describe("FollowupComparisonPanel", () => {
  it("renders consecutive visit deltas and triggers visit graph callback", () => {
    const onInspect = vi.fn();
    const followups: FollowupComparisonItem[] = [
      {
        patient_id: "P101",
        days_between: 24,
        previous_visit: {
          visit_id: "V301",
          visit_date: "2023-08-28",
          admission_type: "Inpatient",
          doctor: "Dr. Stephen Strange",
          diagnoses: [{ diagnosis_id: "D0001", condition: "Hyperlipidemia", status: "Active" }],
          prescriptions: [{ prescription_id: "RX0001", medication_name: "Rosuvastatin", dosage: "Standard", is_effective: true }],
        },
        followup_visit: {
          visit_id: "V302",
          visit_date: "2023-09-21",
          admission_type: "Follow-up",
          doctor: "Dr. Stephen Strange",
          diagnoses: [{ diagnosis_id: "D0002", condition: "Hyperlipidemia", status: "Active" }],
          prescriptions: [{ prescription_id: "RX0002", medication_name: "Rosuvastatin", dosage: "Standard", is_effective: true }],
        },
        lab_comparisons: [
          {
            biomarker: "LDL Cholesterol",
            unit: "mg/dL",
            v1_test_id: "T0001",
            v1_value: 183.1,
            v2_test_id: "T0002",
            v2_value: 136.8,
            absolute_change: -46.3,
            percentage_change: -25.29,
            direction: "decreased",
          },
        ],
      },
    ];

    render(
      <FollowupComparisonPanel
        followups={followups}
        onInspectVisitGraph={onInspect}
      />
    );
    expect(screen.getByText(/24 days elapsed/i)).toBeInTheDocument();
    expect(screen.getByText(/-46.30 mg\/dL/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "V301" }));
    expect(onInspect).toHaveBeenCalledWith("V301");
  });
});

describe("MedicationAnalyticsView", () => {
  it("displays observational disclaimer, neutral highest rate label, and expandable evidence", async () => {
    render(<MedicationAnalyticsView />);
    expect(
      await screen.findByText(/Highest Observed Improvement Rate/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Academic & Observational Disclaimer/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Metformin \(83.3%, n=12\)/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Inspect/i }));
    expect(screen.getByText(/RX0004/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "P102" }));
    expect(mockOpenPatient).toHaveBeenCalledWith("P102", "followups");
  });
});

describe("AiAssistantView", () => {
  it("submits query, renders clickable citations, and shows grounding warning", async () => {
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
    render(<AiAssistantView />);

    expect(screen.getByText(/Isolated Patient Context:/i)).toBeInTheDocument();

    const textarea = screen.getByPlaceholderText(/Ask about patient P101/i);
    fireEvent.change(textarea, { target: { value: "Summarize P101" } });
    fireEvent.click(screen.getByRole("button", { name: /Send/i }));

    await waitFor(() => {
      expect(screen.getByText(/Patient P101 visited on V301/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Grounding notice:/i)).toBeInTheDocument();
    expect(screen.getAllByText("V999").length).toBeGreaterThanOrEqual(1);

    fireEvent.click(screen.getByRole("button", { name: /P101\s*Patient/i }));
    expect(mockOpenPatient).toHaveBeenCalledWith("P101", "overview");
  });
});
