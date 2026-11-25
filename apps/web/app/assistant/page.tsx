import React, { Suspense } from "react";
import { AiAssistantView } from "@/components/assistant/ai-assistant";
import { Skeleton } from "@/components/ui/skeleton";

export default function AssistantPage() {
  return (
    <Suspense fallback={<Skeleton className="h-[600px] w-full rounded-xl" />}>
      <AiAssistantView />
    </Suspense>
  );
}
