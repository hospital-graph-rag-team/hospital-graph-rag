"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { usePathname, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import type { HealthStatus, PatientDirectoryItem } from "@/types/clinical";

type ThemeMode = "dark" | "light";

interface ClinicalContextValue {
  theme: ThemeMode;
  toggleTheme: () => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  selectedPatientId: string | null;
  setSelectedPatientId: (id: string | null) => void;
  clearSelectedPatient: () => void;
  selectedPatient: PatientDirectoryItem | null;
  patients: PatientDirectoryItem[];
  patientsLoading: boolean;
  health: HealthStatus | null;
  refreshHealth: () => Promise<void>;
  refreshPatients: () => Promise<void>;
  openPatient: (patientId: string, tab?: string, visitId?: string) => void;
  openGraph: (patientId?: string | null, visitId?: string) => void;
  askAssistant: (prompt?: string, patientId?: string | null) => void;
  openAnalytics: (condition?: string) => void;
  demoGateRequired: boolean;
  demoUnlocked: boolean;
  demoChecked: boolean;
  unlockDemo: (code: string) => Promise<void>;
}

const ClinicalContext = createContext<ClinicalContextValue | undefined>(undefined);

export function ClinicalProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [theme, setTheme] = useState<ThemeMode>("dark");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [selectedPatientId, setSelectedPatientIdState] = useState<string | null>(null);
  const [patients, setPatients] = useState<PatientDirectoryItem[]>([]);
  const [patientsLoading, setPatientsLoading] = useState(true);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [demoGateRequired, setDemoGateRequired] = useState(false);
  const [demoUnlocked, setDemoUnlocked] = useState(true);
  const [demoChecked, setDemoChecked] = useState(false);

  useEffect(() => {
    try {
      const savedTheme = localStorage.getItem("cg_theme") as ThemeMode | null;
      if (savedTheme === "light" || savedTheme === "dark") {
        setTheme(savedTheme);
      }
      const urlParams = new URLSearchParams(window.location.search);
      if (!urlParams.get("patientId")) {
        const savedPid = localStorage.getItem("cg_selected_patient");
        if (savedPid && /^P\d{2,6}$/.test(savedPid)) {
          setSelectedPatientIdState((prev) => prev ?? savedPid);
        }
      }
    } catch {
      // Ignore storage access errors
    }
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("dark", "light");
    root.classList.add(theme);
    try {
      localStorage.setItem("cg_theme", theme);
    } catch {
      // Ignore
    }
  }, [theme]);

  const setSelectedPatientId = useCallback((id: string | null) => {
    setSelectedPatientIdState(id);
    try {
      if (id) {
        localStorage.setItem("cg_selected_patient", id);
      } else {
        localStorage.removeItem("cg_selected_patient");
      }
    } catch {
      // Ignore
    }
  }, []);

  const clearSelectedPatient = useCallback(() => {
    setSelectedPatientId(null);
    if (typeof window !== "undefined") {
      const sp = new URLSearchParams(window.location.search);
      if (sp.has("patientId") || sp.has("visitId")) {
        sp.delete("patientId");
        sp.delete("visitId");
        const qs = sp.toString();
        router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
      }
    }
  }, [pathname, router, setSelectedPatientId]);

  const refreshHealth = useCallback(async () => {
    try {
      const h = await apiClient.getHealth();
      setHealth(h);
    } catch {
      setHealth(null);
    }
  }, []);

  const refreshPatients = useCallback(async () => {
    setPatientsLoading(true);
    try {
      const res = await apiClient.getPatients();
      setPatients(res.patients);
    } catch {
      // Keep existing patients if transient error
    } finally {
      setPatientsLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    async function bootstrap() {
      try {
        const gate = await apiClient.checkDemoAccess();
        if (!active) return;
        setDemoGateRequired(gate.required);
        setDemoUnlocked(gate.unlocked);
        setDemoChecked(true);
        await refreshHealth();
        if (gate.unlocked) {
          await refreshPatients();
        } else {
          setPatientsLoading(false);
        }
      } catch {
        if (!active) return;
        setDemoChecked(true);
        await refreshHealth();
        await refreshPatients();
      }
    }
    bootstrap();
    return () => {
      active = false;
    };
  }, [refreshHealth, refreshPatients]);

  const unlockDemo = useCallback(
    async (code: string) => {
      await apiClient.unlockDemoAccess(code);
      setDemoUnlocked(true);
      await refreshPatients();
    },
    [refreshPatients]
  );

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  const selectedPatient =
    patients.find((p) => p.patient_id === selectedPatientId) ?? null;

  const openPatient = useCallback(
    (patientId: string, tab: string = "overview", visitId?: string) => {
      setSelectedPatientId(patientId);
      const sp = new URLSearchParams({ patientId, tab });
      if (visitId) sp.set("visitId", visitId);
      router.push(`/patients?${sp.toString()}`);
    },
    [router, setSelectedPatientId]
  );

  const openGraph = useCallback(
    (patientId?: string | null, visitId?: string) => {
      if (patientId) {
        setSelectedPatientId(patientId);
      }
      const sp = new URLSearchParams();
      if (patientId) {
        sp.set("patientId", patientId);
        sp.set("scope", "patient");
      } else {
        sp.set("scope", "cohort");
      }
      if (visitId) sp.set("visitId", visitId);
      const qs = sp.toString();
      router.push(`/graph${qs ? `?${qs}` : ""}`);
    },
    [router, setSelectedPatientId]
  );

  const askAssistant = useCallback(
    (prompt?: string, patientId?: string | null) => {
      if (patientId !== undefined) {
        setSelectedPatientId(patientId);
      }
      const sp = new URLSearchParams();
      if (patientId) sp.set("patientId", patientId);
      if (prompt) sp.set("q", prompt);
      const qs = sp.toString();
      router.push(`/assistant${qs ? `?${qs}` : ""}`);
    },
    [router, setSelectedPatientId]
  );

  const openAnalytics = useCallback(
    (condition?: string) => {
      const sp = new URLSearchParams();
      if (condition) sp.set("condition", condition);
      const qs = sp.toString();
      router.push(`/analytics${qs ? `?${qs}` : ""}`);
    },
    [router]
  );

  return (
    <ClinicalContext.Provider
      value={{
        theme,
        toggleTheme,
        sidebarCollapsed,
        setSidebarCollapsed,
        selectedPatientId,
        setSelectedPatientId,
        clearSelectedPatient,
        selectedPatient,
        patients,
        patientsLoading,
        health,
        refreshHealth,
        refreshPatients,
        openPatient,
        openGraph,
        askAssistant,
        openAnalytics,
        demoGateRequired,
        demoUnlocked,
        demoChecked,
        unlockDemo,
      }}
    >
      {children}
    </ClinicalContext.Provider>
  );
}

export function useClinical() {
  const ctx = useContext(ClinicalContext);
  if (!ctx) {
    throw new Error("useClinical must be used within a ClinicalProvider");
  }
  return ctx;
}
