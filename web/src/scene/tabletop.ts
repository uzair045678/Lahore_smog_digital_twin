export function tabletopScale(worldWidth: number, targetMeters = 1): number {
  if (!Number.isFinite(worldWidth) || worldWidth <= 0) {
    return 1;
  }
  return Math.min(0.01, Math.max(0.001, targetMeters / worldWidth));
}