import type { Manifest } from "./schema";

export async function loadHistory(manifest: Manifest, fetchFn: typeof fetch = fetch): Promise<{ records: any[] }> {
  if (!manifest.history_url.startsWith("https://")) throw new Error("history_url is not absolute HTTPS");
  const response = await fetchFn(manifest.history_url, { cache: "no-store" });
  if (!response.ok) throw new Error(`history request failed: ${response.status}`);
  const body = await response.json();
  if (!body || !Array.isArray(body.records)) throw new Error("history JSON missing records");
  return body;
}