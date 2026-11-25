import React from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { ClinicalProvider } from "@/components/providers/clinical-provider";
import { PatientExplorer } from "@/components/patients/patient-explorer";
import { KnowledgeGraphView } from "@/components/graph/knowledge-graph-view";
import { AiAssistantView } from "@/components/assistant/ai-assistant";
import { apiClient } from "@/lib/api";

// Controllable Next.js navigation state for simulating router.push / router.replace / Back / Forward
let currentPathname = "/patients";
let currentSearch = "";
const pushCalls: string[] = [];
const replaceCalls: string[] = [];

const mockRouter = {
  push: vi.fn((url: string) => {
    pushCalls.push(url);
    const [path, qs = ""] = url.split("?");
    currentPathname = path;
    currentSearch = qs;
  }),
  replace: vi.fn((url: string) => {
    replaceCalls.push(url);
    const [path, qs = ""] = url.split("?");
    currentPathname = path;
    currentSearch = qs;
  }),
};

vi.mock("next/navigation", () => ({
  usePathname: () => currentPathname,
  useRouter: () => mockRouter,
  useSearchParams: () => new URLSearchParams(currentSearch),
}));

vi.mock("@/components/graph/cytoscape-graph", () => ({
  CytoscapeKnowledgeGraph: ({
    graphData,
  }: {
    graphData: { patient_id?: string | null };
  }) => (
    <div data-testid="mock-cytoscape">
      Graph:{graphData.patient_id || "cohort"}
    </div>
  ),
}));

const MOCK_PATIENTS = [
  {
    patient_id: "P101",
    name: "James Jones",
    dob: "1971-12-21",
    gender: "M",
    age: 54,
    visit_count: 3,
    first_visit_date: "2023-08-28",
    latest_visit_date: "2023-10-18",
    conditions: ["Hyperlipidemia"],
    primary_condition: "Hyperlipidemia",
  },
  {
    patient_id: "P102",
    name: "John Johnson",
    dob: "1998-12-05",
    gender: "M",
    age: 27,
    visit_count: 2,
    first_visit_date: "2024-01-08",
    latest_visit_date: "2024-02-04",
    conditions: ["Type 2 Diabetes"],
    primary_condition: "Type 2 Diabetes",
  },
  {
    patient_id: "P103",
    name: "Charles Miller",
    dob: "1952-11-07",
    gender: "M",
    age: 74,
    visit_count: 2,
    first_visit_date: "2023-04-12",
    latest_visit_date: "2023-05-27",
    conditions: ["Hyperlipidemia"],
    primary_condition: "Hyperlipidemia",
  },
];

function profileFor(pid: string) {
  const p = MOCK_PATIENTS.find((item) => item.patient_id === pid)!;
  return {
    patient_id: p.patient_id,
    name: p.name,
    dob: p.dob,
    gender: p.gender,
    age: p.age,
    visit_count: p.visit_count,
    first_visit_date: p.first_visit_date,
    latest_visit_date: p.latest_visit_date,
    conditions: p.conditions,
    attending_doctors: ["Dr. Stephen Strange"],
  };
}

describe("Patient Selection Architecture Regression Tests", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
    localStorage.clear();
    pushCalls.length = 0;
    replaceCalls.length = 0;
    currentPathname = "/patients";
    currentSearch = "";

    vi.spyOn(apiClient, "checkDemoAccess").mockResolvedValue({
      required: false,
      unlocked: true,
    });
    vi.spyOn(apiClient, "getHealth").mockResolvedValue({
      status: "ok",
      service: "ClinicalGraph API",
      version: "2.0.0",
      environment: "test",
      neo4j_connected: true,
      groq_configured: true,
      model_name: "openai/gpt-oss-120b",
      auth_enabled: false,
      timestamp: new Date().toISOString(),
    });
    vi.spyOn(apiClient, "getPatients").mockResolvedValue({
      total: MOCK_PATIENTS.length,
      patients: MOCK_PATIENTS,
    });
    vi.spyOn(apiClient, "getPatientProfile").mockImplementation(async (pid) =>
      profileFor(pid)
    );
    vi.spyOn(apiClient, "getPatientTimeline").mockImplementation(async (pid) => ({
      patient_id: pid,
      visit_count: 1,
      visits: [],
    }));
    vi.spyOn(apiClient, "getPatientLabTrends").mockImplementation(async (pid) => ({
      patient_id: pid,
      trends: [],
    }));
    vi.spyOn(apiClient, "getPatientFollowups").mockImplementation(async (pid) => ({
      patient_id: pid,
      transition_count: 0,
      followups: [],
    }));
    vi.spyOn(apiClient, "getPatientGraph").mockImplementation(async (pid) => ({
      scope: "patient",
      patient_id: pid,
      nodes: [],
      edges: [],
      stats: {
        node_count: 1,
        edge_count: 0,
        node_counts_by_type: { Patient: 1 },
        edge_counts_by_type: {},
      },
    }));
  });

  it("loads P101 from Quick Patient Exploration URL and switches cleanly to P102 without snapping back", async () => {
    currentSearch = "patientId=P101&tab=overview";

    const { rerender } = render(
      <ClinicalProvider>
        <PatientExplorer />
      </ClinicalProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "James Jones" })).toBeInTheDocument();
    });

    // Switch to P102 in directory
    fireEvent.click(screen.getByRole("button", { name: /P102.*John Johnson/i }));

    // Simulate intermediate render BEFORE router searchParams finishes updating (url still P101)
    rerender(
      <ClinicalProvider>
        <PatientExplorer />
      </ClinicalProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "John Johnson" })).toBeInTheDocument();
    });

    // Ensure router.push updated the URL to P102 and P101 never overrides it
    expect(currentSearch).toContain("patientId=P102");

    // Re-render now that URL reflects P102
    rerender(
      <ClinicalProvider>
        <PatientExplorer />
      </ClinicalProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "John Johnson" })).toBeInTheDocument();
    });
    expect(screen.queryByRole("heading", { name: "James Jones" })).not.toBeInTheDocument();
  });

  it("clears active patient cleanly without auto-selecting first patient and allows immediate re-selection", async () => {
    currentSearch = "patientId=P101&tab=overview";

    const { rerender } = render(
      <ClinicalProvider>
        <PatientExplorer />
      </ClinicalProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "James Jones" })).toBeInTheDocument();
    });

    // Click accessible Clear Patient button
    fireEvent.click(screen.getByRole("button", { name: /Clear selected patient/i }));

    rerender(
      <ClinicalProvider>
        <PatientExplorer />
      </ClinicalProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/No patient selected/i)).toBeInTheDocument();
    });

    expect(currentSearch).not.toContain("patientId=");
    expect(localStorage.getItem("cg_selected_patient")).toBeNull();
    expect(screen.queryByRole("heading", { name: "James Jones" })).not.toBeInTheDocument();

    // Immediately select P103 after clearing
    fireEvent.click(
      screen.getAllByRole("button", { name: /P103.*Charles Miller/i })[0]
    );

    rerender(
      <ClinicalProvider>
        <PatientExplorer />
      </ClinicalProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Charles Miller" })).toBeInTheDocument();
    });
    expect(currentSearch).toContain("patientId=P103");
  });

  it("prevents out-of-order API responses from overwriting the latest selected patient", async () => {
    currentSearch = "patientId=P101&tab=overview";

    let resolveP102Profile!: (val: ReturnType<typeof profileFor>) => void;
    const p102Promise = new Promise<ReturnType<typeof profileFor>>((res) => {
      resolveP102Profile = res;
    });

    vi.spyOn(apiClient, "getPatientProfile").mockImplementation(async (pid) => {
      if (pid === "P102") return p102Promise;
      return profileFor(pid);
    });

    const { rerender } = render(
      <ClinicalProvider>
        <PatientExplorer />
      </ClinicalProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "James Jones" })).toBeInTheDocument();
    });

    // Click P102 (slow response) then immediately click P103 (fast response)
    fireEvent.click(screen.getByRole("button", { name: /P102.*John Johnson/i }));
    fireEvent.click(screen.getByRole("button", { name: /P103.*Charles Miller/i }));

    rerender(
      <ClinicalProvider>
        <PatientExplorer />
      </ClinicalProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Charles Miller" })).toBeInTheDocument();
    });

    // Now resolve slow P102 response AFTER P103 has already rendered
    await act(async () => {
      resolveP102Profile(profileFor("P102"));
    });

    // P103 must remain displayed; slow P102 response must be ignored
    expect(screen.getByRole("heading", { name: "Charles Miller" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "John Johnson" })).not.toBeInTheDocument();
  });

  it("synchronizes patient selection cleanly in KnowledgeGraphView and AiAssistantView", async () => {
    currentPathname = "/graph";
    currentSearch = "patientId=P101&scope=patient";

    const { rerender } = render(
      <ClinicalProvider>
        <KnowledgeGraphView />
      </ClinicalProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("mock-cytoscape")).toHaveTextContent("Graph:P101");
    });

    fireEvent.change(
      screen.getByLabelText("Select patient for knowledge graph"),
      { target: { value: "P102" } }
    );

    rerender(
      <ClinicalProvider>
        <KnowledgeGraphView />
      </ClinicalProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("mock-cytoscape")).toHaveTextContent("Graph:P102");
    });
    expect(currentSearch).toContain("patientId=P102");

    // Verify AiAssistantView inherits P102 and can switch to General Cohort cleanly
    currentPathname = "/assistant";
    currentSearch = "patientId=P102";

    const assistantRender = render(
      <ClinicalProvider>
        <AiAssistantView />
      </ClinicalProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Isolated Patient Context:/i)).toBeInTheDocument();
      expect(
        (screen.getByLabelText("Select AI Assistant context") as HTMLSelectElement).value
      ).toBe("P102");
    });

    fireEvent.change(screen.getByLabelText("Select AI Assistant context"), {
      target: { value: "" },
    });

    assistantRender.rerender(
      <ClinicalProvider>
        <AiAssistantView />
      </ClinicalProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Cohort Context:/i)).toBeInTheDocument();
    });
    expect(currentSearch).not.toContain("patientId=");
  });
});
