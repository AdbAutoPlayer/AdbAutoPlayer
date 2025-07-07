import { GetUISettings, RegisterGlobalHotkeys } from "$lib/wailsjs/go/main/App";
import { setLocale } from "$lib/i18n/i18n";
import { LogError } from "$lib/wailsjs/runtime";
import Locales from "$lib/i18n/locales";
import { config } from "$lib/wailsjs/go/models";
import { showErrorToast } from "$lib/utils/error";

const DEFAULT_THEME = "catppuccin";

export function applyUISettings(settings: config.UIConfig) {
  console.log("Applying UI:", settings);
  document.documentElement.setAttribute("data-theme", settings.Theme);
  setLocale(settings.Language);
}

export async function applyUISettingsFromFile() {
  try {
    const settings = await GetUISettings();
    applyUISettings(settings);
  } catch (error) {
    LogError(`Failed to load UI settings: ${error}`);
    document.documentElement.setAttribute("data-theme", DEFAULT_THEME);
    setLocale(Locales.en.toString());
  }
}

export async function registerGlobalHotkeys() {
  try {
    await RegisterGlobalHotkeys();
  } catch (error) {
    showErrorToast(error, {
      title: "Failed to register Global Stop HotKey",
    });
  }
}
