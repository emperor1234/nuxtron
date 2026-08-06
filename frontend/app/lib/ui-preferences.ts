import { apiGet, apiPatch, DEFAULT_TENANT_ID, STORAGE_TENANT_KEY } from './api-client';

type UiPreferencePatch = {
  ui_nav_role?: 'admin' | 'operator' | 'analyst';
  ui_density?: 'comfortable' | 'compact';
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function resolveTenantId(): string {
  if (!globalThis.window) return DEFAULT_TENANT_ID;
  return globalThis.localStorage?.getItem(STORAGE_TENANT_KEY)?.trim() || DEFAULT_TENANT_ID;
}

function extractTenantSettings(payload: unknown, tenantId: string): Record<string, unknown> {
  if (!isRecord(payload)) return {};
  const tenants = payload.tenants;
  if (!Array.isArray(tenants)) return {};

  const tenant = tenants.find((item) => isRecord(item) && item.tenant_id === tenantId);
  if (!isRecord(tenant)) return {};
  return isRecord(tenant.settings) ? tenant.settings : {};
}

export async function persistUiPreferences(preferences: UiPreferencePatch): Promise<void> {
  const tenantId = resolveTenantId();

  try {
    const tenantList = await apiGet('/tenants', tenantId);
    const existingSettings = extractTenantSettings(tenantList, tenantId);
    await apiPatch(`/tenants/${tenantId}`, { settings: { ...existingSettings, ...preferences } }, tenantId);
  } catch {
    // Preference persistence is best-effort; UI cookies still keep local behavior.
  }
}
