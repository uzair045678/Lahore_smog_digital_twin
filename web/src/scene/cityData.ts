export interface CityData {
  coordinate_system: string;
  origin: { lat: number; lon: number; z: number; description: string };
  boundary: Array<{ lat: number; lon: number; x: number; y: number }>;
  stations: Array<{
    id: string;
    name: string;
    lat: number;
    lon: number;
    x: number;
    y: number;
    inside_boundary: boolean;
    verified: boolean;
  }>;
  station_count: number;
  boundary_point_count: number;
  road_count: number;
  sources: Record<string, string>;
}

export async function loadCityData(url = "./city/lahore.json"): Promise<CityData> {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`city geometry request failed: ${response.status}`);
  return (await response.json()) as CityData;
}