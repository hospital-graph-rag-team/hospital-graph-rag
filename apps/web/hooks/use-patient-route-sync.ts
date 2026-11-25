"use client";

import { useCallback, useEffect, useRef } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useClinical } from "@/components/providers/clinical-provider";

const VALID_PID = /^P\d{2,6}$/;

export function usePatientRouteSync() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { selectedPatientId, setSelectedPatientId } = useClinical();

  const rawUrlPid = searchParams.get("patientId");
  const urlPatientId =
    rawUrlPid && VALID_PID.test(rawUrlPid.trim()) ? rawUrlPid.trim() : null;

  const prevUrlPidRef = useRef<string | null | undefined>(undefined);
  const pendingUrlPidRef = useRef<string | null | undefined>(undefined);

  useEffect(() => {
    if (pendingUrlPidRef.current !== undefined) {
      if (urlPatientId === pendingUrlPidRef.current) {
        pendingUrlPidRef.current = undefined;
        prevUrlPidRef.current = urlPatientId;
      }
      return;
    }

    const prevUrl = prevUrlPidRef.current;
    prevUrlPidRef.current = urlPatientId;

    if (prevUrl === undefined) {
      if (urlPatientId) {
        setSelectedPatientId(urlPatientId);
      }
      return;
    }

    if (urlPatientId !== prevUrl) {
      setSelectedPatientId(urlPatientId);
    }
  }, [urlPatientId, setSelectedPatientId]);

  const selectPatientInRoute = useCallback(
    (
      patientId: string,
      options?: { extraParams?: Record<string, string | null>; replace?: boolean }
    ) => {
      const sp = new URLSearchParams(searchParams.toString());
      const currentUrlPid = sp.get("patientId");
      const hasVisitId = sp.has("visitId");
      const extraChanged = options?.extraParams
        ? Object.entries(options.extraParams).some(([k, v]) =>
            v === null ? sp.has(k) : sp.get(k) !== v
          )
        : false;

      setSelectedPatientId(patientId);

      if (currentUrlPid === patientId && !hasVisitId && !extraChanged) {
        return;
      }

      pendingUrlPidRef.current = patientId;
      prevUrlPidRef.current = patientId;

      sp.set("patientId", patientId);
      sp.delete("visitId");
      if (options?.extraParams) {
        for (const [k, v] of Object.entries(options.extraParams)) {
          if (v === null) sp.delete(k);
          else sp.set(k, v);
        }
      }
      const qs = sp.toString();
      const target = qs ? `${pathname}?${qs}` : pathname;
      if (options?.replace) {
        router.replace(target, { scroll: false });
      } else {
        router.push(target, { scroll: false });
      }
    },
    [pathname, router, searchParams, setSelectedPatientId]
  );

  const clearPatientInRoute = useCallback(
    (options?: { extraParams?: Record<string, string | null>; replace?: boolean }) => {
      const sp = new URLSearchParams(searchParams.toString());
      const hadPatientParam = sp.has("patientId") || sp.has("visitId");
      const extraChanged = options?.extraParams
        ? Object.entries(options.extraParams).some(([k, v]) =>
            v === null ? sp.has(k) : sp.get(k) !== v
          )
        : false;

      setSelectedPatientId(null);

      if (!hadPatientParam && !extraChanged) {
        prevUrlPidRef.current = null;
        return;
      }

      pendingUrlPidRef.current = null;
      prevUrlPidRef.current = null;

      sp.delete("patientId");
      sp.delete("visitId");
      if (options?.extraParams) {
        for (const [k, v] of Object.entries(options.extraParams)) {
          if (v === null) sp.delete(k);
          else sp.set(k, v);
        }
      }
      const qs = sp.toString();
      const target = qs ? `${pathname}?${qs}` : pathname;
      if (options?.replace) {
        router.replace(target, { scroll: false });
      } else {
        router.push(target, { scroll: false });
      }
    },
    [pathname, router, searchParams, setSelectedPatientId]
  );

  return {
    urlPatientId,
    selectedPatientId,
    selectPatientInRoute,
    clearPatientInRoute,
  };
}
