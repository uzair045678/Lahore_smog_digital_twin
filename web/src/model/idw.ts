import { AQI_CONFIG } from "./config.js";

export interface StationValue {
  id: string;
  lat: number;
  lon: number;
  value: number | null;
}

export interface GridPoint {
  lat: number;
  lon: number;
}

export interface InterpolatedResult {
  value: number | null;
  confidence: number;
  nearestDistanceKm: number;
}

export function haversineKm(a: { lat: number; lon: number }, b: { lat: number; lon: number }): number {
  const R = 6371;
  const toRad = Math.PI / 180;
  const dLat = (b.lat - a.lat) * toRad;
  const dLon = (b.lon - a.lon) * toRad;
  const lat1 = a.lat * toRad;
  const lat2 = b.lat * toRad;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

export interface InterpolateOptions {
  power?: number;
  maxRadiusKm?: number;
}

export function interpolate(
  stations: readonly StationValue[],
  point: GridPoint,
  options: InterpolateOptions = {}
): InterpolatedResult {
  const power = options.power ?? AQI_CONFIG.idwPower;
  const maxRadius = options.maxRadiusKm ?? AQI_CONFIG.idwMaxRadiusKm;
  const usable = stations.filter((s) => typeof s.value === "number" && Number.isFinite(s.value as number));

  let nearest = Infinity;
  let totalWeight = 0;
  let weightedSum = 0;

  for (const station of usable) {
    const distance = haversineKm(station, point);
    if (distance < nearest) nearest = distance;
    if (distance === 0) {
      return { value: station.value as number, confidence: 1, nearestDistanceKm: 0 };
    }
    if (distance > maxRadius) continue;
    const weight = 1 / Math.pow(distance, power);
    totalWeight += weight;
    weightedSum += weight * (station.value as number);
  }

  if (!usable.length || totalWeight === 0 || !Number.isFinite(nearest)) {
    return { value: null, confidence: 0, nearestDistanceKm: nearest === Infinity ? Infinity : nearest };
  }

  const confidence = Math.max(0, Math.min(1, 1 - nearest / maxRadius));
  return { value: weightedSum / totalWeight, confidence, nearestDistanceKm: nearest };
}

export function interpolateGrid(
  stations: readonly StationValue[],
  points: readonly GridPoint[],
  options?: InterpolateOptions
): InterpolatedResult[] {
  return points.map((point) => interpolate(stations, point, options));
}