"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  AlertTriangle,
  Bot,
  Check,
  ChevronDown,
  ChevronUp,
  Copy,
  Database,
  Globe,
  Network,
  Plus,
  RefreshCw,
  Send,
  ShieldAlert,
  Square,
  Trash2,
  UserRound,
} from "lucide-react";
import { useClinical } from "@/components/providers/clinical-provider";
import { usePatientRouteSync } from "@/hooks/use-patient-route-sync";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, PanelContent, PanelHeader, PanelTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import {
  citationCategory,
  isPatientCitation,
  isVisitCitation,
} from "@/lib/utils";
import type { ChatThreadMessage } from "@/types/clinical";

export function AiAssistantView() {
  const searchParams = useSearchParams();
  const {
    patients,
    selectedPatient,
    openPatient,
    openGraph,
  } = useClinical();
  const {
    selectedPatientId,
    selectPatientInRoute,
    clearPatientInRoute,
  } = usePatientRouteSync();

  const urlQuery = searchParams.get("q");

  const [messages, setMessages] = useState<ChatThreadMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [expandedAudit, setExpandedAudit] = useState<Record<string, boolean>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [lastFailedPrompt, setLastFailedPrompt] = useState<string | null>(null);

  const activeContextRef = useRef<string | null>(selectedPatientId);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const prefillAppliedRef = useRef<string | null>(null);

  // Isolate conversation history whenever patient context changes
  useEffect(() => {
    if (activeContextRef.current !== selectedPatientId) {
      abortRef.current?.abort();
      setMessages([]);
      setIsLoading(false);
      setLastFailedPrompt(null);
      activeContextRef.current = selectedPatientId;
    }
  }, [selectedPatientId]);

  useEffect(() => {
    if (urlQuery && prefillAppliedRef.current !== urlQuery) {
      prefillAppliedRef.current = urlQuery;
      setInput(urlQuery);
    }
  }, [urlQuery]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const suggestions = selectedPatientId
    ? [
        `Show complete medical history and diagnoses for patient ${selectedPatientId}.`,
        `How have patient ${selectedPatientId}'s laboratory values changed over time?`,
        `Compare patient ${selectedPatientId}'s consecutive follow-up encounters.`,
      ]
    : [
        "Compare synthetic medication outcomes for Type 2 Diabetes.",
        "How many unique patients and visit transitions were analyzed for Hypertension?",
        "Which medication shows the highest observed improvement rate for Hyperlipidemia?",
      ];

  const handleCancel = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsLoading(false);
  };

  const handleClear = () => {
    handleCancel();
    setMessages([]);
    setLastFailedPrompt(null);
  };

  const submitPrompt = useCallback(
    async (promptText: string) => {
      const cleaned = promptText.trim();
      if (!cleaned || isLoading) return;

      const userMsg: ChatThreadMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: cleaned,
        createdAt: new Date().toISOString(),
      };

      const historyPayload = messages
        .filter((m) => !m.isError)
        .slice(-6)
        .map((m) => ({ role: m.role, content: m.content }));

      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setLastFailedPrompt(null);
      setIsLoading(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const res = await apiClient.sendChatQuery(
          {
            query: cleaned,
            selected_patient_id: selectedPatientId,
            conversation_history: historyPayload,
          },
          controller.signal
        );

        const assistantMsg: ChatThreadMessage = {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: res.answer,
          createdAt: new Date().toISOString(),
          response: res,
          isError: res.status === "error",
        };
        setMessages((prev) => [...prev, assistantMsg]);
        if (res.status === "error") {
          setLastFailedPrompt(cleaned);
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") {
          setMessages((prev) => [
            ...prev,
            {
              id: `cancelled-${Date.now()}`,
              role: "assistant",
              content: "Request cancelled before completion.",
              createdAt: new Date().toISOString(),
              isError: true,
            },
          ]);
        } else {
          const errMsg =
            err instanceof Error
              ? err.message
              : "Failed to complete Graph RAG query.";
          setLastFailedPrompt(cleaned);
          setMessages((prev) => [
            ...prev,
            {
              id: `err-${Date.now()}`,
              role: "assistant",
              content: errMsg,
              createdAt: new Date().toISOString(),
              isError: true,
            },
          ]);
        }
      } finally {
        abortRef.current = null;
        setIsLoading(false);
      }
    },
    [isLoading, messages, selectedPatientId]
  );

  const handleCopy = async (id: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 1800);
    } catch {
      // Clipboard unavailable
    }
  };

  const handleCitationClick = (cid: string) => {
    if (isPatientCitation(cid)) {
      openPatient(cid, "overview");
      return;
    }
    if (isVisitCitation(cid)) {
      if (selectedPatientId) {
        openGraph(selectedPatientId, cid);
      } else {
        openGraph(null, cid);
      }
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight text-[var(--cg-text-primary)]">
              Clinical Graph RAG Assistant
            </h1>
            <Badge variant="violet" className="font-mono">
              openai/gpt-oss-120b
            </Badge>
          </div>
          <p className="text-xs text-[var(--cg-text-secondary)]">
            Read-only Groq ReAct agent anchored to live Neo4j Cypher tool calls and citation verification.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            aria-label="Select AI Assistant context"
            value={selectedPatientId || ""}
            onChange={(e) => {
              const val = e.target.value;
              if (val) {
                selectPatientInRoute(val);
              } else {
                clearPatientInRoute();
              }
            }}
            className="h-9 rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-panel)] px-3 text-xs text-[var(--cg-text-primary)]"
          >
            <option value="">General Hospital Cohort</option>
            {patients.map((p) => (
              <option key={p.patient_id} value={p.patient_id}>
                {p.patient_id} — {p.name}
              </option>
            ))}
          </select>

          <Button
            variant="outline"
            size="sm"
            onClick={handleClear}
            disabled={messages.length === 0 && !isLoading}
          >
            <Plus className="h-3.5 w-3.5" />
            New Chat
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClear}
            disabled={messages.length === 0 && !isLoading}
          >
            <Trash2 className="h-3.5 w-3.5" />
            Clear
          </Button>
        </div>
      </div>

      {/* Active Context Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--cg-border)] bg-[var(--cg-bg-panel)] px-4 py-2.5 text-xs">
        <div className="flex items-center gap-2.5">
          {selectedPatientId ? (
            <>
              <UserRound className="h-4 w-4 text-[var(--cg-accent-teal)]" />
              <span>
                <strong className="text-[var(--cg-text-primary)]">
                  Isolated Patient Context:
                </strong>{" "}
                <span className="font-mono text-[var(--cg-accent-teal)]">
                  {selectedPatientId}
                </span>
                {selectedPatient ? ` (${selectedPatient.name})` : ""}
              </span>
            </>
          ) : (
            <>
              <Globe className="h-4 w-4 text-[var(--cg-accent-sky)]" />
              <span>
                <strong className="text-[var(--cg-text-primary)]">
                  Cohort Context:
                </strong>{" "}
                Hospital-wide queries across 50 synthetic patients and 146 visits
              </span>
            </>
          )}
        </div>
        {selectedPatientId && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => openGraph(selectedPatientId)}
          >
            <Network className="h-3.5 w-3.5 text-[var(--cg-accent-sky)]" />
            Inspect Patient Graph
          </Button>
        )}
      </div>

      {/* Chat Workspace */}
      <Panel className="flex flex-col">
        <div className="min-h-[420px] max-h-[600px] overflow-y-auto p-5 space-y-5">
          {messages.length === 0 ? (
            <div className="py-8 text-center space-y-5">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl border border-[#2DD4BF]/30 bg-[#2DD4BF]/10 text-[var(--cg-accent-teal)]">
                <Bot className="h-6 w-6" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-[var(--cg-text-primary)]">
                  Ask a Clinical Knowledge Graph Question
                </h2>
                <p className="mx-auto mt-1 max-w-lg text-xs text-[var(--cg-text-secondary)]">
                  Queries are resolved through multi-hop Neo4j retrieval tools. Citations are checked against retrieved tool evidence, though citation presence does not independently guarantee clinical accuracy.
                </p>
              </div>

              <div className="mx-auto grid max-w-3xl grid-cols-1 gap-2.5 sm:grid-cols-3 text-left">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => submitPrompt(s)}
                    className="rounded-xl border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] p-3.5 text-xs text-[var(--cg-text-secondary)] transition-colors hover:border-[#2DD4BF]/50 hover:text-[var(--cg-text-primary)] cursor-pointer"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => {
              if (msg.role === "user") {
                return (
                  <div key={msg.id} className="flex justify-end">
                    <div className="max-w-2xl rounded-xl border border-[#2DD4BF]/25 bg-[#2DD4BF]/10 px-4 py-3 text-sm text-[var(--cg-text-primary)]">
                      {msg.content}
                    </div>
                  </div>
                );
              }

              const res = msg.response;
              const citations = res?.citations || [];
              const validation = res?.citation_validation;
              const toolCalls = res?.tool_calls || [];
              const evidence = res?.retrieved_evidence || [];
              const isAuditOpen = !!expandedAudit[msg.id];
              const isRefusal = res?.status === "refusal";

              return (
                <div key={msg.id} className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] text-[var(--cg-accent-teal)]">
                    <Bot className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1 space-y-3 rounded-xl border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] p-4">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-[var(--cg-text-primary)]">
                          ClinicalGraph Assistant
                        </span>
                        {isRefusal && (
                          <Badge variant="warning">
                            <ShieldAlert className="h-3 w-3" />
                            Safety Policy
                          </Badge>
                        )}
                        {msg.isError && !isRefusal && (
                          <Badge variant="error">Error</Badge>
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={() => handleCopy(msg.id, msg.content)}
                        className="inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] text-[var(--cg-text-secondary)] hover:bg-[var(--cg-bg-panel)] hover:text-[var(--cg-text-primary)] cursor-pointer"
                      >
                        {copiedId === msg.id ? (
                          <>
                            <Check className="h-3 w-3 text-[var(--cg-success)]" />
                            Copied
                          </>
                        ) : (
                          <>
                            <Copy className="h-3 w-3" />
                            Copy
                          </>
                        )}
                      </button>
                    </div>

                    <div className="max-w-none space-y-2 text-xs sm:text-sm leading-relaxed text-[var(--cg-text-primary)] [&_h1]:text-base [&_h1]:font-semibold [&_h2]:text-sm [&_h2]:font-semibold [&_h3]:text-sm [&_h3]:font-semibold [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:my-0.5 [&_table]:w-full [&_table]:border-collapse [&_th]:border [&_th]:border-[var(--cg-border)] [&_th]:bg-[var(--cg-bg-panel)] [&_th]:px-2.5 [&_th]:py-1.5 [&_th]:text-left [&_td]:border [&_td]:border-[var(--cg-border)] [&_td]:px-2.5 [&_td]:py-1.5 [&_code]:rounded [&_code]:bg-[var(--cg-bg-panel)] [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[0.85em]">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.content}
                      </ReactMarkdown>
                    </div>

                    {/* Citations */}
                    {citations.length > 0 && (
                      <div className="border-t border-[var(--cg-border)] pt-3">
                        <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--cg-text-muted)]">
                          Referenced Identifiers (click Patient or Visit IDs to inspect)
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {citations.map((cid) => {
                            const clickable =
                              isPatientCitation(cid) || isVisitCitation(cid);
                            return clickable ? (
                              <button
                                key={cid}
                                type="button"
                                onClick={() => handleCitationClick(cid)}
                                className="inline-flex items-center gap-1.5 rounded-md border border-[#2DD4BF]/35 bg-[#2DD4BF]/10 px-2 py-0.5 font-mono text-[11px] font-semibold text-[var(--cg-accent-teal)] hover:bg-[#2DD4BF]/20 cursor-pointer"
                              >
                                <span>{cid}</span>
                                <span className="rounded bg-[#2DD4BF]/15 px-1 py-0.2 text-[9px] font-sans font-medium uppercase tracking-wide opacity-85">
                                  {citationCategory(cid)}
                                </span>
                              </button>
                            ) : (
                              <Badge key={cid} variant="neutral" className="font-mono">
                                {cid}
                              </Badge>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Grounding Warning */}
                    {validation && !validation.is_valid && (
                      <div className="flex items-start gap-2 rounded-lg border border-[#FBBF24]/35 bg-[#FBBF24]/10 p-2.5 text-xs text-[var(--cg-warning)]">
                        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                        <span>
                          Grounding notice: Identifier(s){" "}
                          <span className="font-mono font-semibold">
                            {validation.unsupported.join(", ")}
                          </span>{" "}
                          appeared in the response without matching entries in retrieved tool payloads. Verify directly against patient records.
                        </span>
                      </div>
                    )}

                    {/* Tool Calls & Retrieved Evidence */}
                    {(toolCalls.length > 0 || evidence.length > 0) && (
                      <div className="rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-panel)]">
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedAudit((prev) => ({
                              ...prev,
                              [msg.id]: !prev[msg.id],
                            }))
                          }
                          className="flex w-full items-center justify-between px-3 py-2 text-xs font-medium text-[var(--cg-text-secondary)] hover:text-[var(--cg-text-primary)] cursor-pointer"
                        >
                          <span className="flex items-center gap-2">
                            <Database className="h-3.5 w-3.5 text-[var(--cg-accent-sky)]" />
                            Retrieved Evidence & Tool Calls ({toolCalls.length})
                          </span>
                          {isAuditOpen ? (
                            <ChevronUp className="h-3.5 w-3.5" />
                          ) : (
                            <ChevronDown className="h-3.5 w-3.5" />
                          )}
                        </button>
                        {isAuditOpen && (
                          <div className="space-y-3 border-t border-[var(--cg-border)] p-3 text-xs">
                            <div className="space-y-1.5">
                              {toolCalls.map((tc, i) => (
                                <div
                                  key={`${tc.tool}-${i}`}
                                  className="flex flex-wrap items-center justify-between gap-2 rounded border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] px-2.5 py-1.5"
                                >
                                  <span className="font-mono font-semibold text-[var(--cg-accent-teal)]">
                                    {tc.tool}
                                  </span>
                                  <span className="text-[var(--cg-text-secondary)]">
                                    {tc.summary}
                                  </span>
                                </div>
                              ))}
                            </div>
                            {evidence.length > 0 && (
                              <pre className="max-h-56 overflow-auto rounded-lg border border-[var(--cg-border)] bg-[#080C12] p-3 font-mono text-[11px] text-[#94A3B8]">
                                {JSON.stringify(evidence, null, 2)}
                              </pre>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {isLoading && (
            <div className="flex items-center gap-3 rounded-xl border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] p-4 text-xs text-[var(--cg-text-secondary)]">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--cg-accent-teal)] border-t-transparent" />
              <span>
                Dispatching Neo4j retrieval tools and synthesizing response...
              </span>
            </div>
          )}

          {lastFailedPrompt && !isLoading && (
            <div className="flex justify-end">
              <Button
                variant="outline"
                size="sm"
                onClick={() => submitPrompt(lastFailedPrompt)}
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Retry Last Query
              </Button>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Prompt Input */}
        <div className="border-t border-[var(--cg-border)] p-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              submitPrompt(input);
            }}
            className="flex flex-col gap-2 sm:flex-row sm:items-end"
          >
            <div className="flex-1">
              <textarea
                rows={2}
                maxLength={1500}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    submitPrompt(input);
                  }
                }}
                placeholder={
                  selectedPatientId
                    ? `Ask about patient ${selectedPatientId}'s visits, medications, or lab trends...`
                    : "Ask a clinical cohort or patient question (e.g., 'Compare Type 2 Diabetes medication outcomes')..."
                }
                className="w-full resize-none rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] px-3.5 py-2.5 text-sm text-[var(--cg-text-primary)] placeholder:text-[var(--cg-text-muted)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--cg-accent-teal)]"
              />
            </div>
            <div className="flex items-center justify-between gap-2 sm:justify-end">
              <span className="font-mono text-[10px] text-[var(--cg-text-muted)]">
                {input.length}/1500
              </span>
              {isLoading ? (
                <Button type="button" variant="destructive" onClick={handleCancel}>
                  <Square className="h-3.5 w-3.5" />
                  Stop
                </Button>
              ) : (
                <Button type="submit" disabled={!input.trim()}>
                  <Send className="h-3.5 w-3.5" />
                  Send
                </Button>
              )}
            </div>
          </form>
        </div>
      </Panel>

      <Panel>
        <PanelHeader className="py-2.5">
          <PanelTitle className="text-xs text-[var(--cg-text-secondary)]">
            Academic Synthetic Data & Safety Boundaries
          </PanelTitle>
        </PanelHeader>
        <PanelContent className="py-2.5 text-[11px] text-[var(--cg-text-muted)]">
          Read-only access to synthetic Neo4j AuraDB hospital records. Personalized diagnostic or prescribing requests are refused. Conversation history resets automatically when switching patient contexts to prevent cross-patient leakage.
        </PanelContent>
      </Panel>
    </div>
  );
}
