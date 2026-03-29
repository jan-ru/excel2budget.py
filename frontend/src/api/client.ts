/**
 * Typed API client for the Data Conversion Tool backend.
 *
 * Uses `fetch` with generated OpenAPI types. Every call returns a
 * `Result<T>` so callers handle success/error uniformly.
 */
import type { components } from "../types/api";

// ── Type aliases from the generated OpenAPI schema ──────────────────
type OutputTemplate = components["schemas"]["OutputTemplate"];
type DocumentationPack = components["schemas"]["DocumentationPack"];
type ApplicationContextInput = components["schemas"]["ApplicationContext-Input"];
type CustomerConfiguration = components["schemas"]["CustomerConfiguration"];
type CreateConfigurationRequest = components["schemas"]["CreateConfigurationRequest"];
type UpdateConfigurationRequest = components["schemas"]["UpdateConfigurationRequest"];

// ── Result type for consistent error handling ───────────────────────
export type Result<T> =
  | { ok: true; data: T }
  | { ok: false; error: string };

// ── Base URL (configurable via Vite env) ────────────────────────────
const BASE_URL: string =
  (import.meta as Record<string, any>).env?.VITE_API_URL ?? "http://localhost:8000";

// ── Internal helpers ────────────────────────────────────────────────

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<Result<T>> {
  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json", ...init?.headers },
      ...init,
    });

    if (res.status === 204) {
      return { ok: true, data: undefined as unknown as T };
    }

    const body = await res.json();

    if (!res.ok) {
      const detail: string =
        body?.detail ??
        (Array.isArray(body?.detail)
          ? body.detail.map((e: any) => e.msg).join("; ")
          : `HTTP ${res.status}`);
      return { ok: false, error: detail };
    }

    return { ok: true, data: body as T };
  } catch (err) {
    return { ok: false, error: (err as Error).message ?? "Network error" };
  }
}

// ── Template endpoints ──────────────────────────────────────────────

/** GET /api/templates/packages → list of package names */
export async function getPackages(): Promise<Result<string[]>> {
  const result = await request<{ packages: string[] }>(
    "/api/templates/packages",
  );
  return result.ok ? { ok: true, data: result.data.packages } : result;
}

/** GET /api/templates/packages/{pkg}/templates → list of template names */
export async function getTemplates(pkg: string): Promise<Result<string[]>> {
  const result = await request<{ templates: string[] }>(
    `/api/templates/packages/${encodeURIComponent(pkg)}/templates`,
  );
  return result.ok ? { ok: true, data: result.data.templates } : result;
}

/** GET /api/templates/packages/{pkg}/templates/{tpl} → full OutputTemplate */
export async function getTemplate(
  pkg: string,
  tpl: string,
): Promise<Result<OutputTemplate>> {
  const result = await request<{ template: OutputTemplate }>(
    `/api/templates/packages/${encodeURIComponent(pkg)}/templates/${encodeURIComponent(tpl)}`,
  );
  return result.ok ? { ok: true, data: result.data.template } : result;
}

// ── Documentation endpoint ──────────────────────────────────────────

/** POST /api/documentation/generate → DocumentationPack */
export async function generateDocumentation(
  ctx: ApplicationContextInput,
): Promise<Result<DocumentationPack>> {
  return request<DocumentationPack>("/api/documentation/generate", {
    method: "POST",
    body: JSON.stringify(ctx),
  });
}

// ── Configuration endpoints ─────────────────────────────────────────

/** GET /api/configurations → list of all saved configurations */
export async function listConfigurations(): Promise<
  Result<CustomerConfiguration[]>
> {
  const result = await request<{ configurations: CustomerConfiguration[] }>(
    "/api/configurations",
  );
  return result.ok ? { ok: true, data: result.data.configurations } : result;
}

/** GET /api/configurations/{name} → single configuration */
export async function getConfiguration(
  name: string,
): Promise<Result<CustomerConfiguration>> {
  return request<CustomerConfiguration>(
    `/api/configurations/${encodeURIComponent(name)}`,
  );
}

/** POST /api/configurations → create a new configuration */
export async function createConfiguration(
  config: CreateConfigurationRequest,
): Promise<Result<CustomerConfiguration>> {
  return request<CustomerConfiguration>("/api/configurations", {
    method: "POST",
    body: JSON.stringify(config),
  });
}

/** PUT /api/configurations/{name} → update an existing configuration */
export async function updateConfiguration(
  name: string,
  config: UpdateConfigurationRequest,
): Promise<Result<CustomerConfiguration>> {
  return request<CustomerConfiguration>(
    `/api/configurations/${encodeURIComponent(name)}`,
    { method: "PUT", body: JSON.stringify(config) },
  );
}

/** DELETE /api/configurations/{name} → delete a configuration */
export async function deleteConfiguration(
  name: string,
): Promise<Result<void>> {
  return request<void>(
    `/api/configurations/${encodeURIComponent(name)}`,
    { method: "DELETE" },
  );
}
