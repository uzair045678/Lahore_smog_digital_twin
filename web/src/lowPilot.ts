import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

type Stats = { geometry: Record<string, number>; batches: Array<{ category: string; buildingCount: number }>; config: { tolerance_m: number }; materials: number; meshes: number; estimatedDrawCalls: number; assetBytes: number };

const canvas = document.querySelector<HTMLCanvasElement>("#viewer")!;
const hud = document.querySelector<HTMLDivElement>("#hud")!;
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setClearColor(0x0b1118);
const scene = new THREE.Scene();
scene.add(new THREE.HemisphereLight(0xc9e3ff, 0x28313c, 2.2));
const sun = new THREE.DirectionalLight(0xffffff, 2.5); sun.position.set(400, 700, 300); scene.add(sun);
const camera = new THREE.PerspectiveCamera(45, 1, 1, 100000); camera.position.set(8500, 7600, 9000);
const controls = new OrbitControls(camera, canvas); controls.target.set(-1800, 0, 2200); controls.enableDamping = true; controls.maxPolarAngle = Math.PI * 0.49;
const loader = new GLTFLoader();

function resize() { const width = canvas.clientWidth; const height = canvas.clientHeight; renderer.setSize(width, height, false); camera.aspect = width / height; camera.updateProjectionMatrix(); }
addEventListener("resize", resize); resize();

Promise.all([
  new Promise<THREE.Group>((resolve, reject) => loader.load("./low-pilot/low_pilot.glb", (result) => resolve(result.scene), undefined, reject)),
  fetch("./low-pilot/low_pilot.stats.json", { cache: "no-cache" }).then((response) => { if (!response.ok) throw new Error(`stats ${response.status}`); return response.json() as Promise<Stats>; }),
]).then(([model, stats]) => {
  scene.add(model);
  hud.textContent = `LAHORE LOW PILOT\nBuildings: ${stats.geometry.buildingsGenerated.toLocaleString()} | Roads: ${stats.geometry.renderedRoadRecords.toLocaleString()}\nTriangles: ${Math.round(stats.geometry.buildingTriangles).toLocaleString()} | Draw calls: ${stats.estimatedDrawCalls}\nSimplification: ${stats.config.tolerance_m}m (${(100 * (1 - stats.geometry.simplifiedVertices / stats.geometry.originalVertices)).toFixed(2)}%)\nHoles retained: ${stats.geometry.holesRetained}\nX=east, Y=height, Z=-north`;
}).catch((error) => { hud.textContent = `LOW pilot failed to load\n${String(error)}`; console.error(error); });

function animate() { controls.update(); renderer.render(scene, camera); requestAnimationFrame(animate); }
animate();
