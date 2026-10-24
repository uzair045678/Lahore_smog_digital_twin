import { describe, it, expect, vi } from "vitest";
import { LatestData } from "./schema";
import { DataLoadError, fetchLatest, fetchManifest, isStale, loadSnapshot } from "./loader";

describe("data loader", () => {
  const manifest = {
    schema_version: "1.0",
    data_version: "2024-01-01T00-00-00Z",
    published_at: "2024-01-01T00:00:00Z",
    latest_url: "https://example.com/latest.json",
    history_url: "https://example.com/history.json",
  };

  const latest = {
    schema_version: "1.0",
    data_version: "2024-01-01T00-00-00Z",
    generated_at: "2024-01-01T00:00:00Z",
    city: {},
    stations: [{ id: "1", name: "x", lat: 31, lon: 74, altitude: null, observed_at: "2024-01-01T00:00:00Z", fetched_at: "2024-01-01T00:00:00Z", source: "epa", measured: true, aqi: 1, aqi_standard: null, aqi_category: null, aqi_range: null, major_pollutant: null, temperature: null, humidity: null, quality_flags: null }],
    measurements: {},
    forecast: { hourly: {}, wind: [] },
    source_health: {},
  } as LatestData;

  it("fetches and validates manifest", async () => {
    const fetchFn = vi.fn(async () => ({ ok: true, status: 200, statusText: "OK", json: async () => manifest })) as unknown as typeof fetch;
    await expect(fetchManifest(fetchFn)).resolves.toMatchObject({ data_version: manifest.data_version });
  });

  it("rejects invalid manifest", async () => {
    const fetchFn = vi.fn(async () => ({ ok: true, status: 200, statusText: "OK", json: async () => ({ nope: 1 }) })) as unknown as typeof fetch;
    await expect(fetchManifest(fetchFn)).rejects.toBeInstanceOf(DataLoadError);
  });

  it("rejects version mismatch", async () => {
    const fetchFn = vi.fn(async () => ({ ok: true, status: 200, statusText: "OK", json: async () => ({ ...latest, data_version: "different" }) })) as unknown as typeof fetch;
    await expect(fetchLatest(manifest, fetchFn)).rejects.toBeInstanceOf(DataLoadError);
  });

  it("loads matching snapshot", async () => {
    const fetchFn = vi.fn(async () => ({ ok: true, status: 200, statusText: "OK", json: async () => latest })) as unknown as typeof fetch;
    const snapshot = await fetchLatest(manifest, fetchFn);
    expect(snapshot.stations).toHaveLength(1);
  });

  it("loadSnapshot fetches manifest then latest", async () => {
    const fetchFn = vi.fn(async (url: string) => {
      if (url.endsWith("manifest.json")) return { ok: true, status: 200, statusText: "OK", json: async () => manifest } as never;
      return { ok: true, status: 200, statusText: "OK", json: async () => latest } as never;
    });
    const { manifest: gotManifest, latest: gotLatest } = await loadSnapshot(fetchFn as unknown as typeof fetch);
    expect(gotManifest.data_version).toBe(manifest.data_version);
    expect(gotLatest.data_version).toBe(latest.data_version);
  });

  it("isStale uses observed time", () => {
    const old = {
      ...latest,
      stations: [{ ...latest.stations[0], observed_at: "2020-01-01T00:00:00Z" }],
    } as LatestData;
    expect(isStale(old)).toBe(true);
    expect(isStale(latest, new Date("2024-01-01T01:00:00Z"))).toBe(false);
  });
});