import { appLocale } from "$lib/i18n/i18n";
import type { AppSettings } from "$pytauri/_apiTypes";
import { getLocaleOrDefault } from "$lib/i18n/locales";
import { invoke } from "@tauri-apps/api/core";
import { appSettings } from "$lib/stores";
import { showErrorToast } from "$lib/toast/toast-error";
import type { RustSettingsFormResponse } from "$lib/menu/model";

export async function applySettingsFromFile() {
  const data: RustSettingsFormResponse = await invoke("get_app_settings_form");

  await applySettings(data.settings as AppSettings);
}

export async function applySettings(newSettings: AppSettings) {
  appSettings.set(newSettings);
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
