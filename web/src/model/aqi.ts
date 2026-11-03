import { AQI_CONFIG } from "./config.js";

export type AqiValue = number | null;

export function pm25ToAqi(concentration: number | null | undefined): AqiValue {
  if (typeof concentration !== "number" || !Number.isFinite(concentration) || concentration < 0) {
    return null;
  }
  // EPA AQI procedure truncates PM2.5 to 0.1 µg/m³ before interpolation.
  // https://www.epa.gov/system/files/documents/2024-04/2024-pm-naaqs-fr-published.pdf
  const truncated = Math.trunc(concentration * 10) / 10;
  if (truncated > AQI_CONFIG.pm25Max) {
    return 500;
  }
  for (const band of AQI_CONFIG.pm25Breakpoints) {
    if (truncated <= band.cHigh) {
      const spanC = band.cHigh - band.cLow;
      const spanI = band.iHigh - band.iLow;
      if (spanC === 0) return band.iHigh;
      const aqi = (spanI / spanC) * (truncated - band.cLow) + band.iLow;
      return Math.round(aqi);
    }
  }
  return 500;
}
