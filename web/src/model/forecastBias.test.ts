import { describe, it, expect } from "vitest";
import { biasCorrection, applyBias } from "./forecastBias.js";

describe("forecast bias", () => {
  it("computes mean forecast-observed error", () => {
    const result = biasCorrection([10, 20], [8, 16]);
    expect(result.meanError).toBeCloseTo(3, 5);
    expect(result.sampleCount).toBe(2);
    expect(result.applied).toBe(true);
  });
  it("returns not-applied for empty input", () => {
    const result = biasCorrection([], []);
    expect(result.applied).toBe(false);
    expect(result.meanError).toBeNull();
  });
  it("applyBias subtracts correction", () => {
    const result = biasCorrection([10, 20], [8, 16]);
    expect(applyBias([10, 20], result)).toEqual([7, 17]);
  });
  it("applyBias is identity when not applied", () => {
    const result = biasCorrection([], []);
    expect(applyBias([10, 20], result)).toEqual([10, 20]);
  });
});