<script lang="ts">
  import "../app.css";

  import { onMount, onDestroy } from "svelte";
  import { setupExternalLinkHandler } from "$lib/utils/external-links";
  import { applySettingsFromFile, applySettings } from "$lib/utils/settings";
  import { invoke } from "@tauri-apps/api/core";
  import { toaster } from "$lib/toast/toaster-svelte";
  import { Toast } from "@skeletonlabs/skeleton-svelte";
  import { initPostHog } from "$lib/utils/posthog";
  import { logInfo, logError } from "$lib/log/log-events";
  import { getVersion } from "@tauri-apps/api/app";
  import { profiles, settings, ui } from "$lib/stores.svelte";
  import { listen } from "@tauri-apps/api/event";
  import { EventNames } from "$lib/log/eventNames";
  import type {
    ProfileStateUpdate,
    AppSettings,
    Trigger,
    MenuOption,
  } from "$pytauri/_apiTypes";
  import UpdateContainer from "$lib/components/updater/UpdateContainer.svelte";
  import StatusBar from "$lib/components/modern/StatusBar.svelte";
  import ProfileSidebar from "$lib/components/modern/ProfileSidebar.svelte";
  import LogPanel from "$lib/components/modern/LogPanel.svelte";
  import ThemeCustomizer from "$lib/components/modern/ThemeCustomizer.svelte";
  import SchemaForm from "$lib/form/SchemaForm.svelte";
  import type {
    SettingsProps,
    PydanticSettingsFormResponse,
    RustSettingsFormResponse,
  } from "$lib/menu/model";
  import {
    getAdbSettingsForm,
    getGameSettingsForm,
    getProfileState,
    cacheClear,
    debug,
    startTask,
  } from "$pytauri/apiClient";
  import { t } from "$lib/i18n/i18n";

  let { children } = $props();

  let sidebarCollapsed = $state(false);
  let settingsProps: SettingsProps = $state({
    showSettingsForm: false,
    formData: {},
    formSchema: {},
    fileName: "",
    type: undefined,
  });

  $effect(() => {
    document.documentElement.className = ui.theme;
    document.documentElement.style.setProperty(
      "--accent-h",
      ui.accentHue.toString(),
    );
  });

  async function init() {
    await applySettingsFromFile();
    await invoke("show_window");

    const version = await getVersion();
    settings.setVersion(version);
    await logInfo(`App Version: ${version}`);
    initPostHog(version);
  }

  init();

  onMount(() => {
    return setupExternalLinkHandler();
  });

  onMount(() => {
    let unsubscribers: Array<() => void> = [];

    const setupListeners = async () => {
      const stateUnsub = await listen<ProfileStateUpdate>(
        EventNames.PROFILE_STATE_UPDATE,
        (event) => {
          if (
            profiles.timestamp &&
            profiles.timestamp >= event.payload.timestamp
          ) {
            return;
          }
          profiles.states[event.payload.index] = {
            game_menu: event.payload.state.game_menu,
            active_task: event.payload.state.active_task,
            device_id: event.payload.state.device_id,
          };
          profiles.setStates([...profiles.states]);
        },
      );

      unsubscribers.push(stateUnsub);
    };

    setupListeners();
    return () => unsubscribers.forEach((unsub) => unsub());
  });

  async function callDebug() {
    try {
      await debug({ profile_index: profiles.active });
    } catch (error) {
      void logError(String(error));
    }
  }

  function toggleTheme() {
    ui.setTheme(ui.theme === "dark" ? "light" : "dark");
  }

  function handleDocs() {
    invoke("open_docs");
  }

  function toggleSidebar() {
    ui.setSidebarOpen(!ui.sidebarOpen);
  }

  function toggleLog() {
    ui.setLogOpen(!ui.logOpen);
  }

  // --- Global Settings Logic ---
  async function openAppSettingsForm() {
    try {
      const data = (await invoke(
        "get_app_settings_form",
      )) as RustSettingsFormResponse;
      settingsProps = {
        showSettingsForm: true,
        formData: data.settings,
        formSchema: JSON.parse(data.schema),
        fileName: data.file_name,
        type: "app",
      };
    } catch (error) {
      console.error(error);
    }
  }

  const adbQuickActions = $derived.by(() => {
    const profile = profiles.states[profiles.active];
    const options = profile?.game_menu?.menu_options ?? [];
    return options.filter((o) => o.label.includes("Display Size"));
  });

  async function handleQuickAction(option: MenuOption) {
    try {
      await startTask({
        profile_index: profiles.active,
        label: option.label,
        args: option.args,
      });
      closeSettings();
    } catch (error) {
      void logError(String(error));
    }
  }

  async function openAdbSettingsForm() {
    try {
      const data = (await getAdbSettingsForm({
        profile_index: profiles.active,
      })) as PydanticSettingsFormResponse;

      settingsProps = {
        showSettingsForm: true,
        formData: data[0],
        formSchema: data[1],
        fileName: data[2],
        type: "adb",
      };
    } catch (error) {
      console.error(error);
    }
  }

  async function openGameSettingsForm() {
    const profile = profiles.active;
    const game = profiles.states[profile]?.game_menu;
    if (!game) return;

    try {
      const data = (await getGameSettingsForm({
        profile_index: profile,
      })) as PydanticSettingsFormResponse;

      settingsProps = {
        showSettingsForm: true,
        formData: data[0],
        formSchema: data[1],
        fileName: data[2],
        type: "game",
      };
    } catch (error) {
      console.error(error);
    }
  }

  function closeSettings() {
    settingsProps = {
      showSettingsForm: false,
      formData: {},
      formSchema: {},
      fileName: "",
    };
    ui.setShowSettings(false);
  }

  async function onFormSubmit() {
    const profile = profiles.active;
    try {
      if (settingsProps.fileName === "App.toml") {
        const newSettings: AppSettings = await invoke("save_app_settings", {
          settings: settingsProps.formData,
        });
        await applySettings(newSettings);
      } else {
        await invoke("save_settings", {
          profileIndex: profile,
          fileName: settingsProps.fileName,
          jsonData: JSON.stringify(settingsProps.formData),
        });
        if (settingsProps.fileName.endsWith("ADB.toml")) {
          await cacheClear({
            profile_index: profile,
            trigger: EventNames.ADB_SETTINGS_UPDATED as Trigger,
          });
        } else {
          await cacheClear({
            profile_index: profile,
            trigger: EventNames.GAME_SETTINGS_UPDATED as Trigger,
          });
        }
      }
    } catch (e) {
      void logError(String(e));
    }
    closeSettings();
    // Signal state update (this could be improved by a better state sync system)
    window.dispatchEvent(new CustomEvent("trigger-state-update"));
  }

  async function handleAddProfile() {
    if (!settings.settings) return;

    const currentProfiles = settings.settings.profiles?.profiles ?? ["Default"];
    const newProfileName = `Profile ${currentProfiles.length + 1}`;
    const newProfiles = [...currentProfiles, newProfileName];

    try {
      const newSettings = {
        ...settings.settings,
        profiles: {
          ...settings.settings.profiles,
          profiles: newProfiles,
          active_profile: newProfiles.length - 1,
        },
      };

      const savedSettings: AppSettings = await invoke("save_app_settings", {
        settings: newSettings,
      });
      await applySettings(savedSettings);
      void logInfo(`Created new profile: ${newProfileName}`);
    } catch (error) {
      void logError(`Failed to create profile: ${error}`);
    }
  }

  async function handleDeleteProfile(index: number) {
    if (!settings.settings || !settings.settings.profiles?.profiles) return;
    const currentProfiles = settings.settings.profiles.profiles;
    if (currentProfiles.length <= 1) return;

    const newProfiles = currentProfiles.filter((_, i) => i !== index);
    let newActive = settings.settings.profiles.active_profile ?? 0;
    if (newActive === index) {
      newActive = Math.max(0, index - 1);
    } else if (newActive > index) {
      newActive--;
    }

    try {
      const newSettings = {
        ...settings.settings,
        profiles: {
          ...settings.settings.profiles,
          profiles: newProfiles,
          active_profile: newActive,
        },
      };

      const savedSettings: AppSettings = await invoke("save_app_settings", {
        settings: newSettings,
      });
      await applySettings(savedSettings);
      profiles.setStates(profiles.states.filter((_, i) => i !== index));
      profiles.select(newActive);
      void logInfo(`Deleted profile at index ${index}`);
    } catch (error) {
      void logError(`Failed to delete profile: ${error}`);
    }
  }

  async function handleRenameProfile(index: number, newName: string) {
    if (!settings.settings || !settings.settings.profiles?.profiles) return;
    const currentProfiles = [...settings.settings.profiles.profiles];
    currentProfiles[index] = newName;

    try {
      const newSettings = {
        ...settings.settings,
        profiles: {
          ...settings.settings.profiles,
          profiles: currentProfiles,
        },
      };

      const savedSettings: AppSettings = await invoke("save_app_settings", {
        settings: newSettings,
      });
      await applySettings(savedSettings);
      void logInfo(`Renamed profile at index ${index} to ${newName}`);
    } catch (error) {
      void logError(`Failed to rename profile: ${error}`);
    }
  }

  $effect(() => {
    if (ui.showSettings && !settingsProps.showSettingsForm) {
      if (ui.settingsType === "app") {
        openAppSettingsForm();
      } else if (ui.settingsType === "adb") {
        openAdbSettingsForm();
      } else if (ui.settingsType === "game") {
        openGameSettingsForm();
      }
    } else if (!ui.showSettings && settingsProps.showSettingsForm) {
      settingsProps.showSettingsForm = false;
    }
  });
</script>

<Toast.Group {toaster}>
  {#snippet children(toast)}
    <Toast {toast}>
      <Toast.Message>
        <Toast.Title>{toast.title}</Toast.Title>
        {#if toast.description}
          <Toast.Description>{toast.description}</Toast.Description>
        {/if}
      </Toast.Message>
      {#if toast.action}
        <Toast.ActionTrigger>{toast.action.label}</Toast.ActionTrigger>
      {/if}
      <Toast.CloseTrigger />
    </Toast>
  {/snippet}
</Toast.Group>

<div class="app-container {ui.theme}">
  <StatusBar
    theme={ui.theme}
    onToggleTheme={toggleTheme}
    onToggleSidebar={toggleSidebar}
    onToggleLog={toggleLog}
    onDocs={handleDocs}
    onAppSettings={() => {
      ui.setSettingsType("app");
      ui.setShowSettings(true);
    }}
    onGameSettings={() => {
      ui.setSettingsType("game");
      ui.setShowSettings(true);
    }}
    onAdbSettings={() => {
      ui.setSettingsType("adb");
      ui.setShowSettings(true);
    }}
    onDebug={callDebug}
    sidebarOpen={ui.sidebarOpen}
    logOpen={ui.logOpen}
    onCustomizer={() => ui.setCustomizerOpen(!ui.customizerOpen)}
  />

  {#if ui.customizerOpen}
    <ThemeCustomizer onClose={() => ui.setCustomizerOpen(false)} />
  {/if}

  <!-- Global Settings Overlay -->
  {#if settingsProps.showSettingsForm}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div
      class="global-settings-overlay"
      onclick={closeSettings}
      role="presentation"
    >
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <div
        class="settings-card"
        onclick={(e) => e.stopPropagation()}
        role="presentation"
      >
        <div class="settings-header">
          {#if settingsProps.type === "adb" && adbQuickActions.length > 0}
            <div class="quick-actions">
              <div class="quick-actions-title">{$t("Display Utilities")}</div>
              <div class="quick-actions-grid">
                {#each adbQuickActions as action}
                  <button
                    class="action-btn"
                    onclick={() => handleQuickAction(action)}
                  >
                    {action.label}
                  </button>
                {/each}
              </div>
            </div>
          {/if}

          <div class="settings-actions">
            {settingsProps.fileName === "App.toml"
              ? $t("App Settings")
              : $t("Settings")}
          </div>
          <button
            class="close-btn"
            onclick={closeSettings}
            aria-label="Close settings"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              width="18"
              height="18"><path d="M18 6 6 18M6 6l12 12" /></svg
            >
          </button>
        </div>
        <div class="settings-body">
          <SchemaForm bind:settingsProps {onFormSubmit} />
        </div>
      </div>
    </div>
  {/if}

  <div
    class="main-layout"
    class:layout-bottom={settings.settings?.ui?.log_panel_position === "bottom"}
  >
    <div class="content-wrapper">
      {#if ui.sidebarOpen}
        <ProfileSidebar
          collapsed={sidebarCollapsed}
          onAddProfile={handleAddProfile}
          onDeleteProfile={handleDeleteProfile}
          onRenameProfile={handleRenameProfile}
        />
      {/if}

      <main class="content-area">
        <UpdateContainer />
        {@render children()}
      </main>
    </div>

    <LogPanel
      profileIndex={profiles.active}
      onClear={() => {}}
      collapsed={!ui.logOpen}
      position={settings.settings?.ui?.log_panel_position}
    />
  </div>
</div>

<style>
  .app-container {
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: var(--bg-0);
    color: var(--text-1);
    position: relative;
  }

  .main-layout {
    flex: 1;
    display: flex;
    flex-direction: row;
    overflow: hidden;
  }

  .main-layout.layout-bottom {
    flex-direction: column;
  }

  .content-wrapper {
    flex: 1;
    display: flex;
    flex-direction: row;
    overflow: hidden;
  }

  .content-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    position: relative;
  }

  /* Global Settings Overlay Styles */
  .global-settings-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(8px);
    z-index: 2000;
    display: grid;
    place-items: center;
    padding: 40px;
  }

  .settings-card {
    background: var(--bg-1);
    border: 1px solid var(--line);
    border-radius: var(--radius-lg);
    width: 100%;
    max-width: 800px;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
    overflow: hidden;
  }

  .settings-header {
    padding: 16px 20px;
    border-bottom: 1px solid var(--line);
    display: flex;
    flex-direction: column;
    background: var(--bg-2);
  }

  .quick-actions {
    margin-bottom: 24px;
    padding: 16px;
    background: var(--bg-2);
    border: 1px solid var(--line);
    border-radius: 12px;
  }

  .quick-actions-title {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-4);
    margin-bottom: 12px;
  }

  .quick-actions-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .action-btn {
    padding: 10px;
    background: var(--bg-1);
    border: 1px solid var(--line);
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-2);
    cursor: pointer;
    transition: all 0.2s ease;
    text-align: center;
  }

  .action-btn:hover {
    border-color: var(--accent);
    color: var(--accent);
    background: var(--accent-ghost);
  }

  .settings-actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 16px;
    font-weight: 700;
    color: var(--text-1);
  }

  .settings-body {
    flex: 1;
    overflow-y: auto;
  }

  .close-btn {
    color: var(--text-3);
    transition: all var(--dur-1);
    width: 32px;
    height: 32px;
    display: grid;
    place-items: center;
    border-radius: 8px;
  }

  .close-btn:hover {
    background: var(--bg-hover);
    color: var(--text-1);
  }

  /* Premium Toast styles targeting Zag.js components */
  :global([data-scope="toast"][data-part="group"]) {
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 12px;
    pointer-events: none;
    width: calc(100% - 48px);
    max-width: 360px;
  }

  @keyframes toast-enter {
    from {
      opacity: 0;
      transform: translateY(12px) scale(0.96);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  :global([data-scope="toast"][data-part="root"]) {
    display: flex;
    width: 100%;
    align-items: start;
    justify-content: space-between;
    gap: 12px;
    border-radius: var(--radius-lg);
    border: 1px solid var(--line);
    background-color: var(--bg-1);
    padding: 14px 16px;
    box-shadow: var(--shadow);
    backdrop-filter: blur(12px);
    pointer-events: auto;
    animation: toast-enter 0.25s cubic-bezier(0.22, 1, 0.36, 1) forwards;
    position: relative;
    overflow: hidden;
  }

  /* Decorative accent left indicator */
  :global([data-scope="toast"][data-part="root"]::before) {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    width: 4px;
    background-color: var(--accent);
  }

  :global([data-scope="toast"][data-part="root"][data-type="error"]::before) {
    background-color: var(--err);
  }

  :global([data-scope="toast"][data-part="root"][data-type="info"]::before) {
    background-color: var(--accent);
  }

  /* Specific states */
  :global([data-scope="toast"][data-part="root"][data-type="error"]) {
    border-color: oklch(0.7 0.19 25 / 0.3);
    background-color: oklch(0.205 0.01 280 / 0.9);
  }

  :global([data-scope="toast"][data-part="root"][data-type="info"]) {
    border-color: oklch(0.67 0.18 var(--accent-h) / 0.2);
    background-color: oklch(0.205 0.01 280 / 0.9);
  }

  :global([data-scope="toast"][data-part="message"]) {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 3px;
    padding-left: 6px;
  }

  :global([data-scope="toast"][data-part="title"]) {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-1);
    line-height: 1.4;
  }

  :global([data-scope="toast"][data-part="description"]) {
    font-size: 12px;
    color: var(--text-3);
    line-height: 1.4;
  }

  :global([data-scope="toast"][data-part="close-trigger"]) {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border-radius: 4px;
    color: var(--text-3);
    background: transparent;
    transition:
      background var(--dur-1),
      color var(--dur-1);
    cursor: pointer;
    flex-shrink: 0;
  }

  :global([data-scope="toast"][data-part="close-trigger"]:hover) {
    background: var(--bg-hover);
    color: var(--text-1);
  }
</style>
