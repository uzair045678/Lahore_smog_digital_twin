import fs from "node:fs";
import path from "node:path";
import * as THREE from "../web/node_modules/three/build/three.module.js";
import { mergeGeometries } from "../web/node_modules/three/examples/jsm/utils/BufferGeometryUtils.js";
import { GLTFExporter } from "../web/node_modules/three/examples/jsm/exporters/GLTFExporter.js";

const inputPath = path.resolve(process.argv[2] ?? "city-data/pilot/lahore_pilot.json");
const outputDir = path.resolve(process.argv[3] ?? "web/public/low-pilot");
const tolerance = Number(process.argv[4] ?? 0.5);
const config = { tolerance_m: tolerance, max_area_error: 0.02, max_centroid_displacement_m: 0.5, preserve_holes: true };

globalThis.FileReader ??= class FileReader {
  readAsArrayBuffer(blob) { blob.arrayBuffer().then((result) => { this.result = result; this.onloadend?.(); }); }
  readAsDataURL(blob) { blob.arrayBuffer().then((buffer) => { this.result = `data:application/octet-stream;base64,${Buffer.from(buffer).toString("base64")}`; this.onloadend?.(); }); }
};

const pilot = JSON.parse(fs.readFileSync(inputPath, "utf8"));
fs.mkdirSync(outputDir, { recursive: true });

function distanceToSegment(point, a, b) {
  const dx = b[0] - a[0]; const dy = b[1] - a[1];
  if (dx === 0 && dy === 0) return Math.hypot(point[0] - a[0], point[1] - a[1]);
  const t = Math.max(0, Math.min(1, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / (dx * dx + dy * dy)));
  return Math.hypot(point[0] - (a[0] + t * dx), point[1] - (a[1] + t * dy));
}

function rdp(points, epsilon) {
  if (points.length <= 2) return points;
  let maxDistance = epsilon; let index = -1;
  for (let i = 1; i < points.length - 1; i += 1) {
    const distance = distanceToSegment(points[i], points[0], points.at(-1));
    if (distance > maxDistance) { index = i; maxDistance = distance; }
  }
  if (index < 0) return [points[0], points.at(-1)];
  return [...rdp(points.slice(0, index + 1), epsilon).slice(0, -1), ...rdp(points.slice(index), epsilon)];
}

function simplifyRing(ring, epsilon) {
  const open = ring.slice(0, -1);
  if (open.length <= 4) return ring.map((point) => [...point]);
  const simplified = rdp([...open, open[0]], epsilon).slice(0, -1);
  if (simplified.length < 3) return ring.map((point) => [...point]);
  return [...simplified, [...simplified[0]]];
}

function polygonParts(geometry) {
  return geometry.length && typeof geometry[0][0][0] === "number" ? [geometry] : geometry;
}

function ringMetrics(ring) {
  let twiceArea = 0; let cx = 0; let cy = 0;
  for (let i = 0; i < ring.length - 1; i += 1) {
    const [x1, y1] = ring[i]; const [x2, y2] = ring[i + 1]; const cross = x1 * y2 - x2 * y1;
    twiceArea += cross; cx += (x1 + x2) * cross; cy += (y1 + y2) * cross;
  }
  const area = Math.abs(twiceArea / 2);
  return { area, centroid: area ? [cx / (3 * twiceArea), cy / (3 * twiceArea)] : ring[0] };
}

function geometryMetrics(geometry) {
  let area = 0; let centroidX = 0; let centroidY = 0; let vertices = 0; let holes = 0;
  for (const polygon of polygonParts(geometry)) {
    const outer = ringMetrics(polygon[0]); area += outer.area; centroidX += outer.centroid[0] * outer.area; centroidY += outer.centroid[1] * outer.area; vertices += polygon[0].length - 1; holes += polygon.length - 1;
    for (const hole of polygon.slice(1)) { const metric = ringMetrics(hole); area -= metric.area; centroidX -= metric.centroid[0] * metric.area; centroidY -= metric.centroid[1] * metric.area; vertices += hole.length - 1; }
  }
  return { area, centroid: area ? [centroidX / area, centroidY / area] : [0, 0], vertices, holes };
}

function simplifyGeometry(geometry, epsilon) {
  return polygonParts(geometry).map((polygon) => polygon.map((ring, index) => index === 0 || config.preserve_holes ? simplifyRing(ring, epsilon) : ring.map((point) => [...point])));
}

function safeSimplification(record) {
  const original = record.geometry_local_m;
  const simplified = simplifyGeometry(original, config.tolerance_m);
  const before = geometryMetrics(original); const after = geometryMetrics(simplified);
  const areaError = before.area ? Math.abs(after.area - before.area) / before.area : 0;
  const centroidDisplacement = Math.hypot(after.centroid[0] - before.centroid[0], after.centroid[1] - before.centroid[1]);
  const safe = areaError <= config.max_area_error && centroidDisplacement <= config.max_centroid_displacement_m;
  return { geometry: safe ? simplified : original, before, after: safe ? after : before, areaError: safe ? areaError : 0, centroidDisplacement: safe ? centroidDisplacement : 0, usedOriginal: !safe };
}

function shapeFromPolygon(polygon) {
  const shape = new THREE.Shape(polygon[0].map(([x, north]) => new THREE.Vector2(x, north)));
  shape.holes = polygon.slice(1).map((ring) => new THREE.Path(ring.map(([x, north]) => new THREE.Vector2(x, north))));
  return shape;
}

function buildingGeometry(geometry, height) {
  const parts = polygonParts(geometry);
  const geometries = parts.map((polygon) => new THREE.ExtrudeGeometry(shapeFromPolygon(polygon), { depth: height, bevelEnabled: false, curveSegments: 1, steps: 1 }));
  const merged = geometries.length === 1 ? geometries[0] : mergeGeometries(geometries, false);
  merged.rotateX(-Math.PI / 2);
  merged.computeVertexNormals();
  for (const geometryPart of geometries) if (geometryPart !== merged) geometryPart.dispose();
  return merged;
}

function roadSegments(geometry) {
  const lines = geometry.length && typeof geometry[0][0] === "number" ? [geometry] : geometry;
  const positions = [];
  for (const line of lines) for (let i = 0; i < line.length - 1; i += 1) {
    const [x1, n1] = line[i]; const [x2, n2] = line[i + 1];
    positions.push(x1, 0.03, -n1, x2, 0.03, -n2);
  }
  return positions;
}

function roadVertexCount(geometry) {
  return geometry.length && typeof geometry[0][0] === "number" ? geometry.length : geometry.reduce((sum, line) => sum + line.length, 0);
}

const palette = { residential: 0x9aa7b8, commercial: 0xd5a85c, industrial: 0x9b7bb6, institutional: 0x6fb3c8, unknown: 0x7d8b99 };
const batches = new Map(); const featureMap = []; const geometryStats = { buildingsGenerated: 0, buildingsFailed: 0, originalVertices: 0, simplifiedVertices: 0, buildingTriangles: 0, holesRetained: 0, holesOmitted: 0, fallbackToOriginal: 0, maxCentroidDisplacementM: 0, maxAreaError: 0 };
const toleranceMeasurements = [];
for (const candidateTolerance of [0.25, 0.5, 1, 2]) {
  let originalVertices = 0; let simplifiedVertices = 0; let maxAreaError = 0; let maxDisplacement = 0; let unsafe = 0;
  for (const record of pilot.buildings) { const before = geometryMetrics(record.geometry_local_m); const simplified = simplifyGeometry(record.geometry_local_m, candidateTolerance); const after = geometryMetrics(simplified); const areaError = before.area ? Math.abs(after.area - before.area) / before.area : 0; const displacement = Math.hypot(after.centroid[0] - before.centroid[0], after.centroid[1] - before.centroid[1]); originalVertices += before.vertices; simplifiedVertices += after.vertices; maxAreaError = Math.max(maxAreaError, areaError); maxDisplacement = Math.max(maxDisplacement, displacement); unsafe += areaError > config.max_area_error || displacement > config.max_centroid_displacement_m ? 1 : 0; }
  toleranceMeasurements.push({ tolerance_m: candidateTolerance, originalVertices, simplifiedVertices, reduction_percent: Number((100 * (1 - simplifiedVertices / originalVertices)).toFixed(3)), maxAreaError: Number(maxAreaError.toFixed(6)), maxCentroidDisplacementM: Number(maxDisplacement.toFixed(4)), unsafeBuildings: unsafe });
}

for (const record of pilot.buildings) {
  try {
    const simplified = safeSimplification(record); const category = ["house", "residential", "apartments"].includes(record.building_type) ? "residential" : ["commercial", "retail", "office", "hotel"].includes(record.building_type) ? "commercial" : ["industrial", "warehouse"].includes(record.building_type) ? "industrial" : ["school", "hospital", "university", "college"].includes(record.building_type) ? "institutional" : "unknown";
    const geometry = buildingGeometry(simplified.geometry, record.height_m); const firstVertex = geometryStats.simplifiedVertices; const vertexCount = geometry.getAttribute("position").count; const triangleCount = geometry.index ? geometry.index.count / 3 : vertexCount / 3;
    if (!batches.has(category)) batches.set(category, []); batches.get(category).push(geometry); featureMap.push({ building_id: record.building_id, batch: category, first_vertex: firstVertex, vertex_count: vertexCount, triangles: triangleCount, height_m: record.height_m, height_source: record.height_source, original_vertices: simplified.before.vertices, simplified_vertices: simplified.after.vertices, area_error: simplified.areaError, centroid_displacement_m: simplified.centroidDisplacement, used_original: simplified.usedOriginal });
    geometryStats.buildingsGenerated += 1; geometryStats.originalVertices += simplified.before.vertices; geometryStats.simplifiedVertices += simplified.after.vertices; geometryStats.buildingTriangles += triangleCount; geometryStats.holesRetained += simplified.after.holes; geometryStats.fallbackToOriginal += simplified.usedOriginal ? 1 : 0; geometryStats.maxCentroidDisplacementM = Math.max(geometryStats.maxCentroidDisplacementM, simplified.centroidDisplacement); geometryStats.maxAreaError = Math.max(geometryStats.maxAreaError, simplified.areaError);
  } catch (error) { geometryStats.buildingsFailed += 1; featureMap.push({ building_id: record.building_id, failure: String(error) }); }
}

const scene = new THREE.Scene();
for (const [category, geometries] of batches) { const merged = mergeGeometries(geometries, false); merged.computeVertexNormals(); scene.add(new THREE.Mesh(merged, new THREE.MeshStandardMaterial({ color: palette[category], roughness: 0.9, metalness: 0 }))); for (const geometry of geometries) if (geometry !== merged) geometry.dispose(); }
const roadPositions = pilot.roads.flatMap((record) => roadSegments(record.geometry_local_m)); const roadGeometry = new THREE.BufferGeometry(); roadGeometry.setAttribute("position", new THREE.Float32BufferAttribute(roadPositions, 3)); scene.add(new THREE.LineSegments(roadGeometry, new THREE.LineBasicMaterial({ color: 0x263342 })));
const exporter = new GLTFExporter();
const glb = await new Promise((resolve, reject) => exporter.parse(scene, resolve, reject, { binary: true, includeCustomExtensions: false }));
fs.writeFileSync(path.join(outputDir, "low_pilot.glb"), Buffer.from(glb));
fs.writeFileSync(path.join(outputDir, "low_pilot.features.json"), JSON.stringify({ schema_version: "low-pilot-features-v1", coordinate_convention: "Three.js X=east, Y=height, Z=-north", config, features: featureMap }, null, 2));
const stats = { schema_version: "low-pilot-stats-v1", input: inputPath, config, geometry: { ...geometryStats, originalRoadRecords: pilot.roads.length, renderedRoadRecords: pilot.roads.length, omittedRoadRecords: 0, roadOriginalVertices: pilot.roads.reduce((sum, record) => sum + roadVertexCount(record.geometry_local_m), 0), roadSimplifiedVertices: pilot.roads.reduce((sum, record) => sum + roadVertexCount(record.geometry_local_m), 0), roadSegments: roadPositions.length / 6 }, toleranceMeasurements, batches: [...batches.entries()].map(([category, geometries]) => ({ category, buildingCount: geometries.length })), materials: batches.size + 1, meshes: batches.size + 1, estimatedDrawCalls: batches.size + 1, assetBytes: fs.statSync(path.join(outputDir, "low_pilot.glb")).size, buildingFailureIds: featureMap.filter((feature) => feature.failure).map((feature) => feature.building_id) };
fs.writeFileSync(path.join(outputDir, "low_pilot.stats.json"), JSON.stringify(stats, null, 2));
console.log(JSON.stringify(stats, null, 2));
