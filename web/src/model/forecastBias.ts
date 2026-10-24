export interface BiasResult {
  meanError: number | null;
  sampleCount: number;
  applied: boolean;
}

export function biasCorrection(forecast: readonly number[], observed: readonly number[]): BiasResult {
  const n = Math.min(forecast.length, observed.length);
  if (n === 0) return { meanError: null, sampleCount: 0, applied: false };
  let sum = 0;
  let count = 0;
  for (let i = 0; i < n; i++) {
    const f = forecast[i];
    const o = observed[i];
    if (typeof f !== "number" || typeof o !== "number") continue;
    if (!Number.isFinite(f) || !Number.isFinite(o)) continue;
    sum += f - o;
    count++;
  }
  if (count === 0) return { meanError: null, sampleCount: 0, applied: false };
  return { meanError: sum / count, sampleCount: count, applied: true };
}

export function applyBias(forecast: readonly number[], correction: BiasResult): number[] {
  if (!correction.applied || correction.meanError === null) return [...forecast];
  return forecast.map((value) => (typeof value === "number" && Number.isFinite(value) ? value - correction.meanError! : value));
}