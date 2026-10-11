import { appLocale } from "#lib/i18n/i18n.ts";
import type { AppSettings } from "#pytauri/_apiTypes.d.ts";
import { getLocaleOrDefault } from "#lib/i18n/locales.ts";
import { invoke } from "@tauri-apps/api/core";
import { settings, profiles } from "#lib/stores.svelte.ts";
import { showErrorToast } from "#lib/toast/toast-error.ts";
import type { RustSettingsFormResponse } from "#lib/menu/model.ts";

export async function applySettingsFromFile() {
  const data: RustSettingsFormResponse = await invoke("get_app_settings_form");

  await applySettings(data.settings as AppSettings);
}

export async function applySettings(newSettings: AppSettings) {
  settings.setSettings(newSettings);
  const profileCount = newSettings.profiles?.profiles?.length;
  if (profileCount !== undefined && profiles.states.length > profileCount) {
    profiles.setStates(profiles.states.slice(0, profileCount));
  }
  if (newSettings.profiles?.active_profile !== undefined) {
    profiles.select(newSettings.profiles.active_profile);
  }
  try {
    await applyUISettings(newSettings);
  } catch (e) {
    await showErrorToast(e);
  }
}

async function applyUISettings(settings: AppSettings) {
  const ui = settings.ui;
  if (!ui) {
    return;
  }
  if (ui.theme) {
    document.documentElement.setAttribute("data-theme", ui.theme);
  }

  if (ui.locale) {
    const locale = getLocaleOrDefault(ui.locale);
    appLocale.set(locale);
  }
}
