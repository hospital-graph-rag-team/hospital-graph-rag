import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return new Intl.NumberFormat("en-US").format(value);
}

export function formatDateShort(dateStr: string | null | undefined): string {
  if (!dateStr) return "N/A";
  const parsed = new Date(`${dateStr}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return dateStr;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(parsed);
}

export function formatMonthLabel(monthStr: string): string {
  const [year, month] = monthStr.split("-");
  if (!year || !month) return monthStr;
  const parsed = new Date(Number(year), Number(month) - 1, 1);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    year: "2-digit",
  }).format(parsed);
}

export function isPatientCitation(id: string): boolean {
  return /^P\d{2,6}$/.test(id);
}

export function isVisitCitation(id: string): boolean {
  return /^V\d{2,6}$/.test(id);
}

export function citationCategory(id: string): string {
  if (/^P\d{2,6}$/.test(id)) return "Patient";
  if (/^V\d{2,6}$/.test(id)) return "Visit";
  if (/^DOC\d{2,6}$/.test(id)) return "Doctor";
  if (/^D\d{2,6}$/.test(id)) return "Diagnosis";
  if (/^RX\d{2,6}$/.test(id)) return "Prescription";
  if (/^T\d{2,6}$/.test(id)) return "LabTest";
  return "Entity";
}
