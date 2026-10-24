import { CityScene, type Pollutant } from "./scene/CityScene.js";
import { startDataPolling } from "./data/polling.js";
import { loadHistory } from "./data/history.js";
import { buildTimeline, formatClock, timelineSegment } from "./model/time.js";
import type { LatestData, Manifest } from "./data/schema";

const canvas = document.getElementById("scene") as HTMLCanvasElement;
const status = document.getElementById("status") as HTMLElement;
const stationList = document.getElementById("stationList") as HTMLElement;
const pollutantSelect = document.getElementById("pollutant") as HTMLSelectElement;
const playButton = document.getElementById("play") as HTMLButtonElement;
const previousButton = document.getElementById("previous") as HTMLButtonElement;
const nextButton = document.getElementById("next") as HTMLButtonElement;
const scrubber = document.getElementById("scrubber") as HTMLInputElement;
const timeLabel = document.getElementById("timeLabel") as HTMLElement;
const sourceLabel = document.getElementById("sourceLabel") as HTMLElement;

const scene = new CityScene(canvas);
let selectedPollutant: Pollutant = "pm25";
let latestSnapshot: LatestData | null = null;
let historySnapshot: { records: Array<Record<string, unknown>> } | null = null;
let historyLoaded = false;
let currentIndex = 48;
const timeline = buildTimeline(new Date());
let playing = false;
let autoTimer: number | undefined;

function averaging(values: Array<number | null>): number | null {
  const finite = values.filter((value): value is number => typeof value === "number" && Number.isFinite(value));
  return finite.length ? finite.reduce((sum, value) => sum + value, 0) / finite.length : null;
}

function stationReading(snapshot: LatestData, stationId: string, pollutant: Pollutant): number | null {
  return snapshot.measurements[stationId]?.find((entry) => entry.pollutant === pollutant)?.concentration ?? null;
}

function cityPollutantBaseline(snapshot: LatestData, pollutant: Pollutant): number | null {
  return averaging(snapshot.stations.map((station) => stationReading(snapshot, station.id, pollutant)));
}

function cityAverageAqi(snapshot: LatestData): number | null {
  const value = snapshot.city.average_aqi;
  return typeof value === "number" && Number.isFinite(value) ? value : averaging(snapshot.stations.map((station) => station.aqi ?? null));
}

function averageWindEpaStyle(snapshot: LatestData): { east: number; north: number; speed: number } {
  const samples = snapshot.forecast.wind.slice(Math.max(0, snapshot.forecast.wind.length - Math.min(30, snapshot.forecast.wind.length)));
  let east = 0;
  let north = 0;
  let count = 0;
  for (const sample of samples) {
    const degrees = (sample.direction_degrees ?? 0) + 180;
    const radians = (degrees * Math.PI) / 180;
    const meters = sample.speed * (sample.units === "m/s" ? 1 : 0.27778);
    east += Math.sin(radians) * meters * 0.01;
    north += Math.cos(radians) * meters * 0.01;
    count += 1;
  }
  if (count === 0) return { east: 0, north: 0, speed: 0 };
  return { east: east / count, north: north / count, speed: Math.hypot(east, north) / count };
}

function degreesToVector(speed: number, direction: number, units: string): { east: number; north: number } {
  const metersPerSecond = units === "km/h" ? speed / 3.6 : units === "m/s" ? speed : speed * 0.27778;
  const east = Math.sin(((direction + 180) * Math.PI) / 180) * metersPerSecond * 0.01;
  const north = Math.cos(((direction + 180) * Math.PI) / 180) * metersPerSecond * 0.01;
  return { east, north };
}

function nearestForecastWind(snapshot: LatestData, target: string) {
  const entries = Object.entries(snapshot.forecast.hourly ?? {})
    .map(([timestamp, value]) => ({ timestamp, entry: value as Record<string, unknown> }))
    .filter((item) => Number.isFinite(Date.parse(item.timestamp)));
  if (entries.length === 0) return snapshot.forecast.wind[0]?.direction_degrees != null
    ? { speed: snapshot.forecast.wind[0].speed, direction: snapshot.forecast.wind[0].direction_degrees, units: snapshot.forecast.wind[0].units ?? "m/s" }
    : null;
  let chosen = entries[0];
  let bestDelta = Math.abs(Date.parse(entries[0].timestamp) - Date.parse(target));
  for (const item of entries.slice(1)) {
    const delta = Math.abs(Date.parse(item.timestamp) - Date.parse(target));
    if (delta < bestDelta) {
      chosen = item;
      bestDelta = delta;
    }
  }
  const windSpeed = chosen.entry.wind_speed;
  const windDirection = chosen.entry.wind_direction;
  if (typeof windSpeed !== "number" || typeof windDirection !== "number") return null;
  return { speed: windSpeed, direction: windDirection, units: "km/h" };
}

function historicalRecordAt(index: number): Record<string, unknown> | null {
  if (!historySnapshot || index >= 48) return null;
  return historySnapshot.records[index] ?? null;
}

function historyWind(record: Record<string, unknown> | null) {
  if (!record) return null;
  const speed = typeof record.wind_speed === "number" ? record.wind_speed : null;
  const direction = typeof record.wind_direction === "number" ? record.wind_direction : null;
  if (speed == null || direction == null) return null;
  return { speed, direction, units: speed > 5 ? "km/h" : "m/s" };
}

function factorForIndex(index: number): number {
  if (index === 48 || !latestSnapshot) return 1;
  if (index > 48) {
    const baseline = cityAverageAqi(latestSnapshot);
    const target = timeline[index];
    let forecastAqi: number | null = null;
    for (const [timestamp, value] of Object.entries(latestSnapshot.forecast.hourly ?? {})) {
      const typed = value as Record<string, unknown>;
      if (timestamp === target || (typed && typeof typed.aqi === "number" && timestamp.startsWith(target.slice(0, 13)))) {
        forecastAqi = typed.aqi as number;
        break;
      }
    }
    if (forecastAqi == null || baseline == null || baseline === 0) return 1;
    return Math.min(Math.max(forecastAqi / baseline, 0.25), 4);
  }
  const record = historicalRecordAt(index);
  if (!record) return 1;
  const baseline = cityPollutantBaseline(latestSnapshot, selectedPollutant);
  const historicalPollutant = record.pollutants && selectedPollutant in (record.pollutants as Record<string, number>)
    ? (record.pollutants as Record<string, number | null>)[selectedPollutant]
    : null;
  if (typeof historicalPollutant === "number" && typeof baseline === "number" && baseline !== 0) {
    return Math.min(Math.max(historicalPollutant / baseline, 0.25), 4);
  }
  if (typeof record.aqi === "number" && cityAverageAqi(latestSnapshot)) {
    return (record.aqi as number) / (cityAverageAqi(latestSnapshot) as number);
  }
  return 1;
}

function windForIndex(index: number): { east: number; north: number } {
  if (!latestSnapshot) return { east: 0, north: 0 };
  if (index === 48) return averageWindEpaStyle(latestSnapshot);
  if (index > 48) {
    const wind = nearestForecastWind(latestSnapshot, timeline[index]);
    if (wind) return degreesToVector(wind.speed, wind.direction, wind.units);
    return averageWindEpaStyle(latestSnapshot);
  }
  const record = historicalRecordAt(index);
  const wind = historyWind(record);
  if (wind) return degreesToVector(wind.speed, wind.direction, wind.units);
  if (latestSnapshot.forecast.wind.length) {
    const sample = latestSnapshot.forecast.wind[0];
    return degreesToVector(sample.speed, sample.direction_degrees ?? 0, sample.units ?? "m/s");
  }
  return { east: 0, north: 0 };
}

function segmentForIndex(index: number): string {
  const segment = timelineSegment(index);
  return segment === "past" ? "Past observation" : segment === "future" ? "City forecast, modelled" : "Live EPA observation";
}

function isMeasuredForIndex(index: number): boolean {
  return index === 48;
}

function sourceForIndex(index: number): string {
  if (index === 48) return "Punjab EPA current dashboard";
  if (index > 48) return "Open-Meteo forecast (city scale)";
  return "EPA 48-hour city-average history";
}

function renderTimeUI(snapshot: LatestData | null) {
  if (!snapshot) return;
  scrubber.value = String(currentIndex);
  timeLabel.textContent = `${formatClock(timeline[currentIndex])} — ${segmentForIndex(currentIndex)}`;
  const current = cityPollutantBaseline(snapshot, selectedPollutant);
  sourceLabel.textContent = `${sourceForIndex(currentIndex)} · ${isMeasuredForIndex(currentIndex) ? "measured" : "modelled"} · city average ${current == null ? "n/a" : current.toFixed(1)} (${selectedPollutant.toUpperCase()})`;
  stationList.textContent = snapshot.stations
    .map((station) => {
      const base = stationReading(snapshot, station.id, selectedPollutant);
      const projected = base == null ? "n/a" : (base * factorForIndex(currentIndex)).toFixed(1);
      return `${station.name}: ${stationReadiness(base)} -> ${projected}`;
    })
    .join(" · ");
}

function stationReadiness(value: number | null): string {
  return value == null ? "n/a" : value.toFixed(1);
}

function updateScene(): void {
  if (!latestSnapshot) return;
  scene.setSnapshot(latestSnapshot, selectedPollutant);
  const factor = factorForIndex(currentIndex);
  const wind = windForIndex(currentIndex);
  scene.setTimeSample(factor, wind.east, wind.north);
  status.textContent = `${description(latestSnapshot)} · ${formatClock(timeline[currentIndex])} · ${segmentForIndex(currentIndex)}`;
  renderTimeUI(latestSnapshot);
}

function description(snapshot: LatestData): string {
  const observed = latestSnapshot?.stations.map((station) => station.observed_at ?? "").sort().pop() ?? "unknown";
  return `Live: ${snapshot.stations.length} stations · version ${snapshot.data_version} · observed ${observed}`;
}

async function loadHistorySafely(manifest: Manifest) {
  try {
    historySnapshot = await loadHistory(manifest);
    updateScene();
  } catch (error) {
    historySnapshot = null;
    status.textContent = `Data unavailable for history: ${error instanceof Error ? error.message : String(error)}`;
  }
}

void scene.ready
  .then(() => {
    const controller = startDataPolling({
      onUpdate: (snapshot) => {
        latestSnapshot = snapshot.latest;
        if (!historyLoaded) {
          historyLoaded = true;
          void loadHistorySafely(snapshot.manifest);
        }
        updateScene();
      },
      onError: (error) => {
        status.textContent = "Data unavailable: " + (error instanceof Error ? error.message : String(error));
      },
    });
    window.addEventListener("beforeunload", () => controller.stop());
  })
  .catch((error: unknown) => {
    status.textContent = "Scene failed to initialise: " + (error instanceof Error ? error.message : String(error));
  });

scrubber.addEventListener("input", () => {
  currentIndex = Math.max(0, Math.min(timeline.length - 1, Number(scrubber.value)));
  updateScene();
});

previousButton.addEventListener("click", () => {
  currentIndex = Math.max(0, currentIndex - 1);
  updateScene();
});

nextButton.addEventListener("click", () => {
  currentIndex = Math.min(timeline.length - 1, currentIndex + 1);
  updateScene();
});

playButton.addEventListener("click", () => {
  playing = !playing;
  playButton.textContent = playing ? "Pause" : "Play";
  if (playing) {
    autoTimer = window.setInterval(() => {
      currentIndex = currentIndex >= timeline.length - 1 ? 0 : currentIndex + 1;
      updateScene();
    }, 750);
  } else if (autoTimer) {
    clearInterval(autoTimer);
    autoTimer = undefined;
  }
});

pollutantSelect.addEventListener("change", () => {
  selectedPollutant = pollutantSelect.value as Pollutant;
  updateScene();
});

window.addEventListener("beforeunload", () => {
  if (autoTimer) clearInterval(autoTimer);
});