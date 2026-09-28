import type { AppSettings, ProfileState } from "$pytauri/_apiTypes";

class ProfileStore {
  active = $state<number>(0);
  states = $state<ProfileState[]>([]);
  timestamp = $state<number | null>(null);
  // ms; profile state events requested before this may carry a stale index.
  listChangedAt = 0;

  select(index: number) {
    this.active = index;
  }

  setStates(states: ProfileState[]) {
    this.states = states;
  }

  updateState(index: number, state: Partial<ProfileState>) {
    if (this.states[index]) {
      this.states[index] = { ...this.states[index], ...state };
    }
  }

  setTimestamp(ts: number | null) {
    this.timestamp = ts;
  }
}

class SettingsStore {
  settings = $state<AppSettings | null>(null);
  appVersion = $state<string>("");
  debugLogLevelOverwrite = $state<boolean[]>([false]);

  setSettings(settings: AppSettings | null) {
    this.settings = settings;
  }

  setVersion(version: string) {
    this.appVersion = version;
  }

  setDebugLogLevelOverwrite(overwrite: boolean[]) {
    this.debugLogLevelOverwrite = overwrite;
  }

  updateDebugLogLevelOverwrite(index: number, value: boolean) {
    this.debugLogLevelOverwrite[index] = value;
    // trigger reactivity
    this.debugLogLevelOverwrite = [...this.debugLogLevelOverwrite];
  }
}

const defaultUiState = {
  showSettings: false,
  settingsType: "adb" as "adb" | "game" | "app",
  sidebarOpen: true,
  logOpen: true,
  theme: "dark" as "dark" | "light",
  accentHue: 272,
  customizerOpen: false,
  taskViewVariant: "cards" as "cards" | "palette" | "accordion",
  // Seasonal event modes most users don't need; applies until the user
  // hides/unhides any card, after which their saved list is used.
  hiddenTasks: [
    "AFK Journey::FrostfireShowdown",
    "AFK Journey::SunlitShowdown",
  ] as string[],
  showHiddenTasks: false,
};

class UiStore {
  showSettings = $state(defaultUiState.showSettings);
  settingsType = $state(defaultUiState.settingsType);
  sidebarOpen = $state(defaultUiState.sidebarOpen);
  logOpen = $state(defaultUiState.logOpen);
  theme = $state(defaultUiState.theme);
  accentHue = $state(defaultUiState.accentHue);
  customizerOpen = $state(defaultUiState.customizerOpen);
  taskViewVariant = $state(defaultUiState.taskViewVariant);
  hiddenTasks = $state<string[]>([...defaultUiState.hiddenTasks]);
  showHiddenTasks = $state(defaultUiState.showHiddenTasks);

  constructor() {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("uiState");
        if (saved) {
          const parsed = JSON.parse(saved);
          if (parsed.sidebarOpen !== undefined)
            this.sidebarOpen = parsed.sidebarOpen;
          if (parsed.logOpen !== undefined) this.logOpen = parsed.logOpen;
          if (parsed.theme !== undefined) this.theme = parsed.theme;
          if (parsed.accentHue !== undefined) this.accentHue = parsed.accentHue;
          if (parsed.taskViewVariant !== undefined)
            this.taskViewVariant = parsed.taskViewVariant;
          if (Array.isArray(parsed.hiddenTasks))
            this.hiddenTasks = parsed.hiddenTasks;
          if (parsed.showHiddenTasks !== undefined)
            this.showHiddenTasks = parsed.showHiddenTasks;
        }
      } catch (e) {
        console.error("Failed to load uiState from localStorage", e);
      }
    }
  }

  save() {
    if (typeof window !== "undefined") {
      try {
        const stateToSave = {
          sidebarOpen: this.sidebarOpen,
          logOpen: this.logOpen,
          theme: this.theme,
          accentHue: this.accentHue,
          taskViewVariant: this.taskViewVariant,
          hiddenTasks: this.hiddenTasks,
          showHiddenTasks: this.showHiddenTasks,
        };
        localStorage.setItem("uiState", JSON.stringify(stateToSave));
      } catch (e) {
        console.error("Failed to save uiState to localStorage", e);
      }
    }
  }

  setShowSettings(show: boolean) {
    this.showSettings = show;
  }

  setSettingsType(type: "adb" | "game" | "app") {
    this.settingsType = type;
  }

  setSidebarOpen(open: boolean) {
    this.sidebarOpen = open;
    this.save();
  }

  setLogOpen(open: boolean) {
    this.logOpen = open;
    this.save();
  }

  setTheme(theme: "dark" | "light") {
    this.theme = theme;
    this.save();
  }

  setAccentHue(hue: number) {
    this.accentHue = hue;
    this.save();
  }

  setCustomizerOpen(open: boolean) {
    this.customizerOpen = open;
  }

  setTaskViewVariant(variant: "cards" | "palette" | "accordion") {
    this.taskViewVariant = variant;
    this.save();
  }

  isTaskHidden(taskKey: string | undefined): boolean {
    return taskKey !== undefined && this.hiddenTasks.includes(taskKey);
  }

  toggleTaskHidden(taskKey: string) {
    this.hiddenTasks = this.isTaskHidden(taskKey)
      ? this.hiddenTasks.filter((key) => key !== taskKey)
      : [...this.hiddenTasks, taskKey];
    this.save();
  }

  setShowHiddenTasks(show: boolean) {
    this.showHiddenTasks = show;
    this.save();
  }
}

export const profiles = new ProfileStore();
export const settings = new SettingsStore();
export const ui = new UiStore();
