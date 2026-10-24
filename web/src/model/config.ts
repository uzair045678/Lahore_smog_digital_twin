export const AQI_CONFIG = {
  /** US EPA 24-hour PM2.5 -> AQI breakpoints (2024 revision). */
  pm25Breakpoints: [
    { cLow: 0.0, cHigh: 9.0, iLow: 0, iHigh: 50 },
    { cLow: 9.1, cHigh: 35.4, iLow: 51, iHigh: 100 },
    { cLow: 35.5, cHigh: 55.4, iLow: 101, iHigh: 150 },
    { cLow: 55.5, cHigh: 125.4, iLow: 151, iHigh: 200 },
    { cLow: 125.5, cHigh: 225.4, iLow: 201, iHigh: 300 },
    { cLow: 225.5, cHigh: 325.4, iLow: 301, iHigh: 400 },
    { cLow: 325.5, cHigh: 500.4, iLow: 401, iHigh: 500 },
  ] as const,
  /** Concentration above this is reported as the top of the scale. */
  pm25Max: 500.4,
  /** Confidence drops to zero beyond this distance (km). */
  idwMaxRadiusKm: 15,
  /** IDW power parameter. */
  idwPower: 2,
  /** Time window for live scene. */
  historyHours: 48,
  forecastHours: 24,
  stepHours: 1,
  /** Whether to correct forecast to observed values (disabled by default). */
  biasCorrectionEnabled: false,
} as const;