import React, { Suspense } from "react";
import { MedicationAnalyticsView } from "@/components/analytics/medication-analytics";
import { Skeleton } from "@/components/ui/skeleton";

export default function AnalyticsPage() {
  return (
    <Suspense fallback={<Skeleton className="h-[600px] w-full rounded-xl" />}>
      <MedicationAnalyticsView />
    </Suspense>
  );
}
