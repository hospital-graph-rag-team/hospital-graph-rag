import { AlertTriangle, Inbox, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Panel } from "@/components/ui/card";

export function ErrorState({
  title = "Unable to load clinical data",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <Panel className="border-[var(--cg-error)]/30 bg-[var(--cg-bg-panel)] p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--cg-error)]/10 text-[var(--cg-error)]">
            <AlertTriangle className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-[var(--cg-text-primary)]">
              {title}
            </h4>
            <p className="mt-1 text-xs text-[var(--cg-text-secondary)] max-w-xl">
              {message}
            </p>
          </div>
        </div>
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            <RefreshCw className="h-3.5 w-3.5" />
            Retry
          </Button>
        )}
      </div>
    </Panel>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <Panel className="p-8 text-center">
      <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] text-[var(--cg-text-secondary)]">
        <Inbox className="h-5 w-5" />
      </div>
      <h4 className="mt-3 text-sm font-semibold text-[var(--cg-text-primary)]">
        {title}
      </h4>
      <p className="mx-auto mt-1 max-w-md text-xs text-[var(--cg-text-secondary)]">
        {description}
      </p>
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </Panel>
  );
}
