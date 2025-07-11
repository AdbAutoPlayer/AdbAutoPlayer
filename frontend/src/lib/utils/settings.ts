import { setLocale } from "$lib/i18n/i18n";
import Locales from "$lib/i18n/locales";
import { showErrorToast } from "$lib/utils/error";
import { GetGeneralSettings } from "@wails/settings/settingsservice";
import { UISettings } from "@wails/settings";
import { RegisterGlobalHotkeys } from "@wails/hotkeys/hotkeysservice";
import { LogError } from "$lib/utils/logger";

const DEFAULT_THEME = "catppuccin";

export function applyUISettings(settings: UISettings) {
  document.documentElement.setAttribute("data-theme", settings.Theme);
  setLocale(settings.Language);
}

export async function applyUISettingsFromFile() {
  try {
    const settings = await GetGeneralSettings();
    applyUISettings(settings["User Interface"]);
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
