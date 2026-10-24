import { describe, it, expect } from "vitest";
import { pm25ToAqi } from "./aqi.js";

describe("pm25ToAqi", () => {
  it("returns null for invalid input", () => {
    expect(pm25ToAqi(null)).toBeNull();
    expect(pm25ToAqi(undefined)).toBeNull();
    expect(pm25ToAqi(NaN)).toBeNull();
    expect(pm25ToAqi(-1)).toBeNull();
  });
  it("maps breakpoint edges exactly", () => {
    expect(pm25ToAqi(0)).toBe(0);
    expect(pm25ToAqi(9.0)).toBe(50);
    expect(pm25ToAqi(9.1)).toBe(51);
    expect(pm25ToAqi(35.4)).toBe(100);
    expect(pm25ToAqi(35.5)).toBe(101);
    expect(pm25ToAqi(55.4)).toBe(150);
    expect(pm25ToAqi(55.5)).toBe(151);
    expect(pm25ToAqi(125.4)).toBe(200);
    expect(pm25ToAqi(125.5)).toBe(201);
    expect(pm25ToAqi(225.4)).toBe(300);
    expect(pm25ToAqi(225.5)).toBe(301);
    expect(pm25ToAqi(325.4)).toBe(400);
    expect(pm25ToAqi(325.5)).toBe(401);
    expect(pm25ToAqi(500.4)).toBe(500);
  });
  it("caps values beyond scale at 500", () => {
    expect(pm25ToAqi(600)).toBe(500);
  });
});