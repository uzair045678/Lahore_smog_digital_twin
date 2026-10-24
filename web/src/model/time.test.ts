import { describe, it, expect } from "vitest";
import { buildTimeline, nearestValue, hourKey } from "./time.js";

describe("time", () => {
  it("hourKey is zero-padded UTC", () => {
    expect(hourKey(new Date("2024-01-02T03:04:05Z"))).toBe("2024-01-02T03:00:00Z");
  });
  it("buildTimeline includes history + forecast hours", () => {
    const now = new Date("2024-06-01T12:00:00Z");
    const result = buildTimeline(now);
    expect(result.length).toBe(72);
    expect(result[0]).toBe("2024-05-30T12:00:00Z");
    expect(result[result.length - 1]).toBe("2024-06-02T11:00:00Z");
  });
  it("nearestValue returns closest within 90 min", () => {
    const series = [
      { timestamp: "2024-06-01T10:00:00Z", value: 5 },
      { timestamp: "2024-06-01T12:00:00Z", value: 9 },
    ];
    expect(nearestValue(series, "2024-06-01T11:30:00Z")).toBe(9);
  });
  it("nearestValue returns null beyond 90 min", () => {
    const series = [{ timestamp: "2024-06-01T10:00:00Z", value: 5 }];
    expect(nearestValue(series, "2024-06-01T13:00:00Z")).toBeNull();
  });
});