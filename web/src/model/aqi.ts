import { AQI_CONFIG } from "./config.js";

export type AqiValue = number | null;

export function pm25ToAqi(concentration: number | null | undefined): AqiValue {
  if (typeof concentration !== "number" || !Number.isFinite(concentration) || concentration < 0) {
    return null;
  }
  if (concentration > AQI_CONFIG.pm25Max) {
    return 500;
  }
  for (const band of AQI_CONFIG.pm25Breakpoints) {
    if (concentration <= band.cHigh) {
      const spanC = band.cHigh - band.cLow;
      const spanI = band.iHigh - band.iLow;
      if (spanC === 0) return band.iHigh;
      const aqi = (spanI / spanC) * (concentration - band.cLow) + band.iLow;
      return Math.round(aqi);
    }
  }
  return 500;
}