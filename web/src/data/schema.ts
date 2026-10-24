export interface Manifest {
  schema_version: string;
  data_version: string;
  published_at: string;
  latest_url: string;
  history_url: string;
}

export interface WindVector {
  timestamp: string;
  position: { lat: number; lon: number } | null;
  coverage: string;
  speed: number;
  units: string;
  direction: "from" | "toward";
  direction_degrees: number | null;
  measured: boolean;
  source: string;
}

export interface PollutantReading {
  pollutant: string;
  concentration: number | null;
  measured: boolean | null;
  units: string | null;
  observed_at: string | null;
  source: string;
}

export interface Station {
  id: string;
  name: string;
  lat: number;
  lon: number;
  altitude: number | null;
  observed_at: string | null;
  fetched_at: string;
  source: string;
  measured: boolean | null;
  aqi: number | null;
  aqi_standard: string | null;
  aqi_category: string | null;
  aqi_range: string | null;
  major_pollutant: string | null;
  temperature: number | null;
  humidity: number | null;
  quality_flags: Record<string, unknown> | null;
}

export interface LatestData {
  schema_version: string;
  data_version: string;
  generated_at: string;
  city: Record<string, unknown>;
  stations: Station[];
  measurements: Record<string, PollutantReading[]>;
  forecast: { hourly: Record<string, unknown>; wind: WindVector[] };
  source_health: Record<string, unknown>;
}
