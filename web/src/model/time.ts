import { AQI_CONFIG } from "./config.js";

export function hourKey(date: Date): string {
  const y = date.getUTCFullYear();
  const m = String(date.getUTCMonth() + 1).padStart(2, "0");
  const d = String(date.getUTCDate()).padStart(2, "0");
  const h = String(date.getUTCHours()).padStart(2, "0");
  return `${y}-${m}-${d}T${h}:00:00Z`;
}

export function buildTimeline(now: Date = new Date(), hours: number = AQI_CONFIG.historyHours + AQI_CONFIG.forecastHours): string[] {
  const start = new Date(now.getTime() - AQI_CONFIG.historyHours * 3600 * 1000);
  const result: string[] = [];
  for (let i = 0; i < hours; i += AQI_CONFIG.stepHours) {
    result.push(hourKey(new Date(start.getTime() + i * 3600 * 1000)));
  }
  return result;
}

export interface TimedValue {
  timestamp: string;
  value: number | null;
}

export function nearestValue(series: readonly TimedValue[], target: string): number | null {
  let best: { delta: number; value: number | null } | null = null;
  const targetMs = Date.parse(target);
  for (const entry of series) {
    const entryMs = Date.parse(entry.timestamp);
    if (!Number.isFinite(entryMs)) continue;
    const delta = Math.abs(entryMs - targetMs);
    if (!best || delta < best.delta) best = { delta, value: entry.value };
  }
  if (!best || best.delta > 90 * 60 * 1000) return null;
  return best.value;
}

export function timelineSegment(index: number, historyLength = AQI_CONFIG.historyHours): "past" | "now" | "future" {
  if (index < historyLength) return "past";
  if (index === historyLength) return "now";
  return "future";
}

export function formatClock(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString(undefined, { weekday: "short", hour: "2-digit", minute: "2-digit", month: "short", day: "numeric" });
}