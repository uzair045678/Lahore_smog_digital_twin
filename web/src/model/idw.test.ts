import { describe, it, expect } from "vitest";
import { haversineKm, interpolate, interpolateGrid } from "./idw.js";
import type { StationValue } from "./idw.js";

describe("idw", () => {
  it("distance is zero for identical points", () => {
    expect(haversineKm({ lat: 31.5, lon: 74.3 }, { lat: 31.5, lon: 74.3 })).toBe(0);
  });
  it("single station gives uniform value at all in-range points", () => {
    const stations: StationValue[] = [{ id: "s1", lat: 31.5, lon: 74.3, value: 42 }];
    const result = interpolate(stations, { lat: 31.52, lon: 74.32 });
    expect(result.value).toBe(42);
    expect(result.confidence).toBeGreaterThan(0);
  });
  it("returns null when no station inside radius", () => {
    const stations: StationValue[] = [{ id: "s1", lat: 31.5, lon: 74.3, value: 42 }];
    const result = interpolate(stations, { lat: 0, lon: 0 }, { maxRadiusKm: 1 });
    expect(result.value).toBeNull();
    expect(result.confidence).toBe(0);
  });
  it("null values are ignored", () => {
    const stations: StationValue[] = [
      { id: "s1", lat: 31.5, lon: 74.3, value: null },
      { id: "s2", lat: 31.51, lon: 74.31, value: 10 },
    ];
    const result = interpolate(stations, { lat: 31.505, lon: 74.305 });
    expect(result.value).toBe(10);
  });
  it("interpolates known two-point case with power 1", () => {
    const stations: StationValue[] = [
      { id: "a", lat: 0, lon: 0, value: 0 },
      { id: "b", lat: 0, lon: 2, value: 10 },
    ];
    const result = interpolate(stations, { lat: 0, lon: 1 }, { power: 1, maxRadiusKm: 1000 });
    expect(result.value).toBeCloseTo(5, 5);
  });
  it("grid helper has same length and mapping", () => {
    const stations: StationValue[] = [{ id: "s1", lat: 31.5, lon: 74.3, value: 7 }];
    const points = [{ lat: 31.5, lon: 74.3 }, { lat: 31.51, lon: 74.31 }];
    const out = interpolateGrid(stations, points);
    expect(out.length).toBe(2);
    expect(out[0].value).toBe(7);
  });
});