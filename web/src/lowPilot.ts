import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

type Stats = { geometry: Record<string, number>; config: { tolerance_m: number } };
type Cell = { local_bounds_m?: number[]; building_count: number; road_density_class: string };
type Coverage = { cells: Cell[]; bounds_local_m: number[] };

const canvas = document.querySelector<HTMLCanvasElement>("#viewer")!;
const hud = document.querySelector<HTMLDivElement>("#hud")!;
const params = new URLSearchParams(location.search);
const mode = params.get("mode") ?? "full";
const requestedDpr = params.get("dpr");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(requestedDpr === "native" ? devicePixelRatio : Math.min(Number(requestedDpr) || devicePixelRatio, 2)); renderer.setClearColor(0x0b1118);
const scene = new THREE.Scene(); scene.fog = new THREE.Fog(0x0b1118, 9000, 26000);
scene.add(new THREE.HemisphereLight(0xc9e3ff, 0x28313c, 2.2));
const sun = new THREE.DirectionalLight(0xffffff, 2.8); sun.position.set(400, 700, 300); scene.add(sun);
const camera = new THREE.PerspectiveCamera(45, 1, 1, 100000);
const controls = new OrbitControls(camera, canvas); controls.enableDamping = true; controls.maxPolarAngle = Math.PI * 0.49;
const loader = new GLTFLoader(); let model: THREE.Group; let stats: Stats; let coverage: Coverage; let grid: THREE.Group; let gridVisible = !params.has("grid") || params.get("grid") !== "off"; let minorRoad: THREE.Object3D | undefined; let localRoad: THREE.Object3D | undefined; let lastLodDistance = -1;
const frameTimes: number[] = []; let lastFrame = performance.now(); let frameCounter = 0; const started = performance.now();

function resize() { const width = canvas.clientWidth; const height = canvas.clientHeight; renderer.setSize(width, height, false); camera.aspect = width / height; camera.updateProjectionMatrix(); }
addEventListener("resize", resize); resize();

function cameraPreset(name: string) {
  if (!coverage) return;
  const [west, south, east, north] = coverage.bounds_local_m; const cx = (west + east) / 2; const cz = -(south + north) / 2; const span = Math.max(east - west, north - south);
  const presets: Record<string, [number, number, number, number]> = { overview: [cx + span * 0.85, span * 1.05, cz + span * 0.9, 45], oblique: [cx + span * 0.55, span * 0.52, cz + span * 0.58, 50], top: [cx, span * 1.08, cz, 25], close: [-1800, 1600, 2200, 45] };
  const [x, y, z, fov] = presets[name]; camera.position.set(x, y, z); camera.fov = fov; camera.updateProjectionMatrix(); controls.target.set(cx, 0, cz); controls.update();
}

function makeCoverageGrid() {
  grid = new THREE.Group(); grid.name = "coverage-debug-grid"; const colors: Record<string, number> = { dense: 0x44bb77, sparse: 0xe4a940, zero: 0xe45b5b };
  for (const kind of Object.keys(colors)) {
    const positions: number[] = [];
    for (const cell of coverage.cells) {
      if (!cell.local_bounds_m) continue;
      const [w, s, e, n] = cell.local_bounds_m; const z1 = -s; const z2 = -n; const type = cell.building_count === 0 ? "zero" : cell.building_count <= 1 || cell.road_density_class !== "high" ? "sparse" : "dense";
      if (type === kind) positions.push(w, 0.08, z1, e, 0.08, z1, e, 0.08, z1, e, 0.08, z2, e, 0.08, z2, w, 0.08, z2, w, 0.08, z2, w, 0.08, z1);
    }
    const geometry = new THREE.BufferGeometry(); geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3)); grid.add(new THREE.LineSegments(geometry, new THREE.LineBasicMaterial({ color: colors[kind], transparent: true, opacity: 0.45 })));
  }
  scene.add(grid);
}

function updateRoadLod() { const distance = camera.position.distanceTo(controls.target); if (Math.abs(distance - lastLodDistance) < 25) return; lastLodDistance = distance; if (minorRoad) minorRoad.visible = distance < 6500; if (localRoad) localRoad.visible = distance < 12500; }

function animate(now: number) {
  const delta = now - lastFrame; lastFrame = now; frameTimes.push(delta); if (frameTimes.length > 60) frameTimes.shift(); frameCounter += 1; controls.update(); updateRoadLod(); renderer.render(scene, camera);
  if (stats && frameCounter % 15 === 0) { const average = frameTimes.reduce((sum, value) => sum + value, 0) / frameTimes.length; const info = renderer.info.render; hud.textContent = `LAHORE LOW v2 [${mode}]\nBuildings: ${stats.geometry.buildingsGenerated.toLocaleString()} | Roads: ${stats.geometry.renderedRoadRecords.toLocaleString()}\nFPS: ${(1000 / average).toFixed(1)} | frame: ${average.toFixed(2)} ms\nDraw calls: ${info.calls} | triangles: ${info.triangles.toLocaleString()}\nGeometries: ${renderer.info.memory.geometries} | textures: ${renderer.info.memory.textures}\nDPR: ${devicePixelRatio} → ${renderer.getPixelRatio()} | buffer: ${canvas.width}×${canvas.height}\nGrid: ${gridVisible ? "ON" : "OFF"} | Runtime: ${((now - started) / 1000).toFixed(0)}s`; }
  requestAnimationFrame(animate);
}

Promise.all([
  new Promise<THREE.Group>((resolve, reject) => loader.load("./low-pilot/low_pilot.glb", (result) => resolve(result.scene), undefined, reject)),
  fetch("./low-pilot/low_pilot.stats.json", { cache: "no-cache" }).then((response) => { if (!response.ok) throw new Error(`stats ${response.status}`); return response.json() as Promise<Stats>; }),
  fetch("./low-pilot/low_pilot.coverage.json", { cache: "no-cache" }).then((response) => { if (!response.ok) throw new Error(`coverage ${response.status}`); return response.json() as Promise<Coverage>; }),
]).then(([loadedModel, loadedStats, loadedCoverage]) => { model = loadedModel; stats = loadedStats; coverage = loadedCoverage; scene.add(model); makeCoverageGrid(); minorRoad = model.getObjectByName("road-minor"); localRoad = model.getObjectByName("road-local"); model.traverse((object) => { if (object === model) return; if (mode === "empty") object.visible = false; else if (mode === "roads") object.visible = object.name.startsWith("road-"); else if (mode === "buildings") object.visible = object.name.startsWith("building-"); }); if (mode === "empty" || mode === "roads" || mode === "buildings") { gridVisible = false; grid.visible = false; } cameraPreset("overview"); }).catch((error) => { hud.textContent = `LOW pilot failed to load\n${String(error)}`; console.error(error); });

document.querySelectorAll<HTMLButtonElement>("[data-camera]").forEach((button) => button.addEventListener("click", () => cameraPreset(button.dataset.camera!)));
document.querySelector<HTMLButtonElement>("#grid-toggle")!.addEventListener("click", (event) => { gridVisible = !gridVisible; grid.visible = gridVisible; (event.currentTarget as HTMLButtonElement).textContent = gridVisible ? "Hide coverage grid" : "Show coverage grid"; });
addEventListener("keydown", (event) => { const key = { "1": "overview", "2": "oblique", "3": "top", "4": "close" }[event.key]; if (key) cameraPreset(key); });
requestAnimationFrame(animate);
