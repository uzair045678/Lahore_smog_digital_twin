import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { loadCityData, type CityData } from "./cityData.js";
import { interpolateGrid } from "../model/idw.js";
import type { LatestData } from "../data/schema";

export type Pollutant = "pm25" | "pm10" | "no2" | "so2" | "o3" | "co";

const UNITS_PER_METER = 1 / 100;
const GRID = 44;

function latLonToMeters(lat: number, lon: number, originLat: number, originLon: number) {
  const latRad = (originLat * Math.PI) / 180;
  const x = (lon - originLon) * 111320 * Math.cos(latRad);
  const y = (lat - originLat) * 110540;
  return { x: x * UNITS_PER_METER, y: y * UNITS_PER_METER };
}

function colorFor(value: number | null): [number, number, number] {
  if (value == null || !Number.isFinite(value)) return [0.13, 0.16, 0.2];
  const t = Math.min(value / 150, 1);
  const color = new THREE.Color().setHSL(0.68 - t * 0.68, 0.86, 0.48);
  return [color.r, color.g, color.b];
}

export class CityScene {
  readonly renderer: THREE.WebGLRenderer;
  readonly scene: THREE.Scene;
  readonly camera: THREE.PerspectiveCamera;
  readonly controls: OrbitControls;
  private city: CityData | null = null;
  private boundaryLine: THREE.Line | null = null;
  private stationMeshes: THREE.Mesh[] = [];
  private stationIds: string[] = [];
  private heatmap: THREE.Points | null = null;
  private heatPoints: Array<{ lat: number; lon: number }> = [];
  private latestSnapshot: LatestData | null = null;
  private readonly timeWind = new THREE.Vector3();
  private stationBaseValues = new Map<string, number | null>();
  private timeScale = 1;
  private heatColors: Float32Array | null = null;
  private readonly particleVelocity = new THREE.Vector3();
  private animationId = 0;
  private particles: THREE.Points | null = null;
  private particleArray: Float32Array | null = null;
  private readyPromise: Promise<void>;
  private disposed = false;

  constructor(canvas: HTMLCanvasElement) {
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0b0f14);
    this.camera = new THREE.PerspectiveCamera(58, window.innerWidth / window.innerHeight, 1, 2000);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    const ambient = new THREE.AmbientLight(0xffffff, 0.5);
    this.scene.add(ambient);
    const sun = new THREE.DirectionalLight(0xffffff, 1.05);
    sun.position.set(80, 160, 100);
    this.scene.add(sun);
    this.scene.add(new THREE.GridHelper(450, 16, 0x21262d, 0x161b22));
    this.camera.position.set(0, 230, 260);
    this.controls.target.set(0, 0, 0);
    window.addEventListener("resize", this.handleResize);
    this.animate();
    this.readyPromise = this.initialize();
  }

  get ready(): Promise<void> {
    return this.readyPromise;
  }

  private async initialize(): Promise<void> {
    const city = await loadCityData();
    this.city = city;
    const originLat = city.origin.lat;
    const originLon = city.origin.lon;
    const boundaryPoints = city.boundary.map((point) => {
      const projected = latLonToMeters(point.lat, point.lon, originLat, originLon);
      return new THREE.Vector3(projected.x, 0, projected.y);
    });
    const closed = boundaryPoints.length > 0 ? [...boundaryPoints, boundaryPoints[0]] : boundaryPoints;
    const boundaryGeometry = new THREE.BufferGeometry().setFromPoints(closed);
    this.boundaryLine = new THREE.Line(boundaryGeometry, new THREE.LineBasicMaterial({ color: 0x7d8590, transparent: true, opacity: 0.8, linewidth: 2 }));
    this.scene.add(this.boundaryLine);

    const sphereGeometry = new THREE.SphereGeometry(2.6, 16, 12);
    const sphereMaterial = new THREE.MeshStandardMaterial({ color: 0xf85149, emissive: 0x441111, roughness: 0.35 });
    city.stations.forEach((station) => {
      const mesh = new THREE.Mesh(sphereGeometry, sphereMaterial);
      const projected = latLonToMeters(station.lat, station.lon, originLat, originLon);
      mesh.position.set(projected.x, 4, projected.y);
      mesh.userData.stationId = station.id;
      this.stationMeshes.push(mesh);
      this.stationIds.push(station.id);
      this.scene.add(mesh);
    });

    const minLat = Math.min(...city.boundary.map((point) => point.lat));
    const maxLat = Math.max(...city.boundary.map((point) => point.lat));
    const minLon = Math.min(...city.boundary.map((point) => point.lon));
    const maxLon = Math.max(...city.boundary.map((point) => point.lon));
    const allPoints: Array<{ lat: number; lon: number }> = [];
    const allProjected: Array<{ x: number; y: number }> = [];
    for (let row = 0; row < GRID; row++) {
      for (let col = 0; col < GRID; col++) {
        const lat = minLat + (maxLat - minLat) * (row / (GRID - 1));
        const lon = minLon + (maxLon - minLon) * (col / (GRID - 1));
        allPoints.push({ lat, lon });
        allProjected.push(latLonToMeters(lat, lon, originLat, originLon));
      }
    }
    this.heatPoints = allPoints;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(allProjected.length * 3);
    allProjected.forEach((point, index) => {
      positions[index * 3] = point.x;
      positions[index * 3 + 1] = 1.2;
      positions[index * 3 + 2] = point.y;
    });
    const colors = new Float32Array(allProjected.length * 3);
    this.heatColors = colors;
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    const material = new THREE.PointsMaterial({ size: 4.8, vertexColors: true, transparent: true, opacity: 0.78, sizeAttenuation: true });
    this.heatmap = new THREE.Points(geometry, material);
    this.scene.add(this.heatmap);

    const particleCount = 900;
    const particlePositions = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount; i++) {
      const lat = minLat + (maxLat - minLat) * Math.random();
      const lon = minLon + (maxLon - minLon) * Math.random();
      const projected = latLonToMeters(lat, lon, originLat, originLon);
      particlePositions[i * 3] = projected.x;
      particlePositions[i * 3 + 1] = 1 + Math.random() * 2;
      particlePositions[i * 3 + 2] = projected.y;
    }
    this.particleArray = particlePositions;
    const particleGeometry = new THREE.BufferGeometry();
    particleGeometry.setAttribute("position", new THREE.BufferAttribute(particlePositions, 3));
    const particleMaterial = new THREE.PointsMaterial({ size: 1.4, color: 0x79c0ff, transparent: true, opacity: 0.75, sizeAttenuation: true });
    this.particles = new THREE.Points(particleGeometry, particleMaterial);
    this.scene.add(this.particles);
  }

  public setSnapshot(snapshot: LatestData, pollutant: Pollutant): void {
    this.latestSnapshot = snapshot;
    this.stationBaseValues.clear();
    snapshot.stations.forEach((station) => {
      const measurement = snapshot.measurements[station.id]?.find((entry) => entry.pollutant === pollutant);
      const value = measurement?.concentration ?? (pollutant === "pm25" && station.aqi != null ? (station.aqi / 10) : null);
      this.stationBaseValues.set(station.id, typeof value === "number" ? value : null);
    });
    this.timeScale = 1;
    const windVector = this.averageWind(snapshot);
    this.particleVelocity.set(windVector.east, 0, windVector.north);
    if (this.particles) {
      const material = this.particles.material as THREE.PointsMaterial;
      material.size = windVector.speed > 1 ? 2.2 : 1.6;
    }
    this.refreshVisuals();
  }

  public setTimeSample(scale: number, windEast: number, windNorth: number): void {
    this.timeScale = Math.min(Math.max(scale, 0.2), 5);
    this.timeWind.set(windEast, 0, windNorth);
    this.particleVelocity.copy(this.timeWind);
    this.refreshVisuals();
  }

  private refreshVisuals(): void {
    if (!this.city || !this.latestSnapshot) return;
    const values = new Map<string, number | null>(this.stationBaseValues);
    if (values.size === 0) {
      this.latestSnapshot.stations.forEach((station) => values.set(station.id, null));
    }
    this.stationMeshes.forEach((mesh, index) => {
      const id = this.stationIds[index];
      const base = id ? (values.get(id) ?? null) : null;
      const scaled = base == null ? null : base * this.timeScale;
      const material = mesh.material as THREE.MeshStandardMaterial;
      const color = colorFor(scaled);
      material.color.setRGB(color[0], color[1], color[2]);
      material.emissive.setRGB(color[0] * 0.35, color[1] * 0.35, color[2] * 0.35);
      const newest = scaled == null ? 3 : Math.max(3, Math.min(9, (scaled / 50) * 9));
      mesh.scale.setScalar(newest / 3);
    });

    const sources = this.city.stations.map((station) => ({
      id: station.id,
      lat: station.lat,
      lon: station.lon,
      value: ((values.get(station.id) ?? null) == null ? null : ((values.get(station.id) as number) * this.timeScale)),
    }));
    const results = interpolateGrid(sources, this.heatPoints);
    if (this.heatColors) {
      for (let index = 0; index < results.length; index++) {
        const color = colorFor(results[index].value);
        this.heatColors[index * 3] = color[0];
        this.heatColors[index * 3 + 1] = color[1];
        this.heatColors[index * 3 + 2] = color[2];
      }
      const attribute = this.heatmap?.geometry.getAttribute("color") as THREE.BufferAttribute | undefined;
      if (attribute) attribute.needsUpdate = true;
    }
  }

  private averageWind(snapshot: LatestData): { east: number; north: number; speed: number } {
    const samples = snapshot.forecast.wind.slice(-Math.min(30, snapshot.forecast.wind.length));
    let east = 0;
    let north = 0;
    let count = 0;
    samples.forEach((sample) => {
      const degrees = (sample.direction_degrees ?? 0) + 180;
      const radians = (degrees * Math.PI) / 180;
      const meters = sample.speed * (sample.units === "m/s" ? 1 : 0.27778);
      east += Math.sin(radians) * meters * (1 / 100);
      north += Math.cos(radians) * meters * (1 / 100);
      count += 1;
    });
    if (count === 0) return { east: 0, north: 0, speed: 0 };
    return { east: east / count, north: north / count, speed: Math.hypot(east, north) / count };
  }

  private animate = (): void => {
    if (this.disposed) return;
    this.animationId = requestAnimationFrame(this.animate);
    this.controls.update();
    if (this.particleArray && this.particles) {
      const speed = Math.hypot(this.particleVelocity.x, this.particleVelocity.z);
      if (speed > 0.001) {
        for (let i = 0; i < this.particleArray.length; i += 3) {
          this.particleArray[i] += this.particleVelocity.x;
          this.particleArray[i + 2] += this.particleVelocity.z;
        }
        const attr = this.particles.geometry.getAttribute("position") as THREE.BufferAttribute;
        attr.needsUpdate = true;
      }
    }
    this.renderer.render(this.scene, this.camera);
  };

  private handleResize = (): void => {
    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(window.innerWidth, window.innerHeight);
  };

  public dispose(): void {
    this.disposed = true;
    cancelAnimationFrame(this.animationId);
    window.removeEventListener("resize", this.handleResize);
    this.controls.dispose();
    this.renderer.dispose();
  }
}