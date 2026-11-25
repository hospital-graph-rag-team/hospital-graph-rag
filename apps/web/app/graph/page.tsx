import React, { Suspense } from "react";
import { KnowledgeGraphView } from "@/components/graph/knowledge-graph-view";
import { Skeleton } from "@/components/ui/skeleton";

export default function GraphPage() {
  return (
    <Suspense fallback={<Skeleton className="h-[640px] w-full rounded-xl" />}>
      <KnowledgeGraphView />
    </Suspense>
  );
}
