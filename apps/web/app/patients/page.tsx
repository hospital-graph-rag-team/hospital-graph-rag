"use client";

import React, { Suspense } from "react";
import { CytoscapeKnowledgeGraph } from "@/components/graph/cytoscape-graph";
import { PatientExplorer } from "@/components/patients/patient-explorer";
import { Skeleton } from "@/components/ui/skeleton";

export default function PatientsPage() {
  return (
    <Suspense fallback={<Skeleton className="h-[540px] w-full rounded-xl" />}>
      <PatientExplorer GraphRenderer={CytoscapeKnowledgeGraph} />
    </Suspense>
  );
}
