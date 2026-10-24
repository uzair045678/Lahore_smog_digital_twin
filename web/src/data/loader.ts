import type { LatestData, Manifest } from "./schema";

export const MANIFEST_URL =
  "https://raw.githubusercontent.com/uzair045678/Lahore_smog_digital_twin/data/manifest.json";
export const POLL_INTERVAL_MS = 10 * 60 * 1000;

export class DataLoadError extends Error {
  constructor(message: string, public readonly cause?: unknown) {
    super(message);
    this.name = "DataLoadError";
  }
}

function isManifest(value: unknown): value is Manifest {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.schema_version === "string" &&
    typeof v.data_version === "string" &&
    typeof v.published_at === "string" &&
    typeof v.latest_url === "string" &&
    typeof v.history_url === "string"
  );
}

function isLatest(value: unknown): value is LatestData {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.schema_version === "string" &&
    typeof v.data_version === "string" &&
    typeof v.generated_at === "string" &&
    Array.isArray(v.stations) &&
    typeof v.measurements === "object" &&
    v.measurements !== null
  );
}

export async function fetchManifest(fetchFn: typeof fetch = fetch): Promise<Manifest> {
  const response = await fetchFn(MANIFEST_URL, { cache: "no-store" });
  if (!response.ok) {
    throw new DataLoadError(`manifest request failed: ${response.status} ${response.statusText}`);
  }
  const body = await response.json();
  if (!isManifest(body)) {
    throw new DataLoadError("manifest JSON does not match the expected schema");
  }
  return body;
}

export async function fetchLatest(manifest: Manifest, fetchFn: typeof fetch = fetch): Promise<LatestData> {
  if (!manifest.latest_url.startsWith("https://")) {
    throw new DataLoadError("latest_url is not an absolute HTTPS URL");
  }
  const response = await fetchFn(manifest.latest_url, { cache: "no-store" });
  if (!response.ok) {
    throw new DataLoadError(`latest snapshot request failed: ${response.status}`);
  }
  const body = await response.json();
  if (!isLatest(body)) {
    throw new DataLoadError("latest snapshot JSON does not match the expected schema");
  }
  if (body.data_version !== manifest.data_version) {
    throw new DataLoadError("snapshot version does not match manifest");
  }
  return body;
}

export async function loadSnapshot(fetchFn: typeof fetch = fetch): Promise<{ manifest: Manifest; latest: LatestData }> {
  const manifest = await fetchManifest(fetchFn);
  const latest = await fetchLatest(manifest, fetchFn);
  return { manifest, latest };
}

export function isStale(latest: LatestData, now: Date = new Date(), maxHours = 2): boolean {
  const observed = latest.stations
    .map((station) => (station.observed_at ? Date.parse(station.observed_at) : NaN))
    .filter((value) => Number.isFinite(value));
  const newest = observed.length ? Math.max(...observed) : Date.parse(latest.generated_at);
  return now.getTime() - newest > maxHours * 60 * 60 * 1000;
}