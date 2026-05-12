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
  import {
    profileStates,
    profileStateTimestamp,
    activeProfile,
    uiState,
    appSettings,
    appVersion,
    debugLogLevelOverwrite,
  } from "$lib/stores";
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
    document.documentElement.className = $uiState.theme;
    document.documentElement.style.setProperty(
      "--accent-h",
      $uiState.accentHue.toString(),
    );
  });

  async function init() {
    await applySettingsFromFile();
    await invoke("show_window");

    const version = await getVersion();
    appVersion.set(version);
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
            $profileStateTimestamp &&
            $profileStateTimestamp >= event.payload.timestamp
          ) {
            return;
          }
          $profileStates[event.payload.index] = {
            game_menu: event.payload.state.game_menu,
            active_task: event.payload.state.active_task,
            device_id: event.payload.state.device_id,
          };
          $profileStates = [...$profileStates];
        },
      );

      unsubscribers.push(stateUnsub);
    };

    setupListeners();
    return () => unsubscribers.forEach((unsub) => unsub());
  });

  async function callDebug() {
    try {
      await debug({ profile_index: $activeProfile });
    } catch (error) {
      void logError(String(error));
    }
  }

  function toggleTheme() {
    $uiState.theme = $uiState.theme === "dark" ? "light" : "dark";
  }

  function handleDocs() {
    invoke("open_docs");
  }

  function toggleSidebar() {
    $uiState.sidebarOpen = !$uiState.sidebarOpen;
  }

  function toggleLog() {
    $uiState.logOpen = !$uiState.logOpen;
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
    const profile = $profileStates[$activeProfile];
    const options = profile?.game_menu?.menu_options ?? [];
    return options.filter((o) => o.label.includes("Display Size"));
  });

  async function handleQuickAction(option: MenuOption) {
    try {
      await startTask({
        profile_index: $activeProfile,
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
        profile_index: $activeProfile,
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
    const profile = $activeProfile;
    const game = $profileStates[profile]?.game_menu;
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
    $uiState.showSettings = false;
  }

  async function onFormSubmit() {
    const profile = $activeProfile;
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
    if (!$appSettings) return;

    const currentProfiles = $appSettings.profiles?.profiles ?? ["Default"];
    const newProfileName = `Profile ${currentProfiles.length + 1}`;
    const newProfiles = [...currentProfiles, newProfileName];

    try {
      const newSettings = {
        ...$appSettings,
        profiles: {
          ...$appSettings.profiles,
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
    if (!$appSettings || !$appSettings.profiles?.profiles) return;
    const currentProfiles = $appSettings.profiles.profiles;
    if (currentProfiles.length <= 1) return;

    const newProfiles = currentProfiles.filter((_, i) => i !== index);
    let newActive = $appSettings.profiles.active_profile ?? 0;
    if (newActive === index) {
      newActive = Math.max(0, index - 1);
    } else if (newActive > index) {
      newActive--;
    }

    try {
      const newSettings = {
        ...$appSettings,
        profiles: {
          ...$appSettings.profiles,
          profiles: newProfiles,
          active_profile: newActive,
        },
      };

      const savedSettings: AppSettings = await invoke("save_app_settings", {
        settings: newSettings,
      });
      await applySettings(savedSettings);
      $activeProfile = newActive;
      void logInfo(`Deleted profile at index ${index}`);
    } catch (error) {
      void logError(`Failed to delete profile: ${error}`);
    }
  }

  async function handleRenameProfile(index: number, newName: string) {
    if (!$appSettings || !$appSettings.profiles?.profiles) return;
    const currentProfiles = [...$appSettings.profiles.profiles];
    currentProfiles[index] = newName;

    try {
      const newSettings = {
        ...$appSettings,
        profiles: {
          ...$appSettings.profiles,
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
    if ($uiState.showSettings && !settingsProps.showSettingsForm) {
      if ($uiState.settingsType === "app") {
        openAppSettingsForm();
      } else if ($uiState.settingsType === "adb") {
        openAdbSettingsForm();
      } else if ($uiState.settingsType === "game") {
        openGameSettingsForm();
      }
    } else if (!$uiState.showSettings && settingsProps.showSettingsForm) {
      settingsProps.showSettingsForm = false;
    }
  });
</script>

<Toast.Group {toaster}>
  {#snippet children(toast)}
    <Toast {toast} class="data-[type=error]:preset-tonal-error">
      <Toast.Message>
        <Toast.Title>
          <span class="text-lg">{toast.title}</span>
        </Toast.Title>
        <Toast.Description>
          <p>{toast.description}</p>
        </Toast.Description>
      </Toast.Message>
      <Toast.CloseTrigger />
    </Toast>
  {/snippet}
</Toast.Group>

<div class="app-container {$uiState.theme}">
  <StatusBar
    theme={$uiState.theme}
    onToggleTheme={toggleTheme}
    onToggleSidebar={toggleSidebar}
    onToggleLog={toggleLog}
    onDocs={handleDocs}
    onAppSettings={() => {
      $uiState.settingsType = "app";
      $uiState.showSettings = true;
    }}
    onGameSettings={() => {
      $uiState.settingsType = "game";
      $uiState.showSettings = true;
    }}
    onAdbSettings={() => {
      $uiState.settingsType = "adb";
      $uiState.showSettings = true;
    }}
    onDebug={callDebug}
    sidebarOpen={$uiState.sidebarOpen}
    logOpen={$uiState.logOpen}
    onCustomizer={() => ($uiState.customizerOpen = !$uiState.customizerOpen)}
  />

  {#if $uiState.customizerOpen}
    <ThemeCustomizer onClose={() => ($uiState.customizerOpen = false)} />
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
    class:layout-bottom={$appSettings?.ui?.log_panel_position === "bottom"}
  >
    <div class="content-wrapper">
      {#if $uiState.sidebarOpen}
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
      profileIndex={$activeProfile}
      onClear={() => {}}
      collapsed={!$uiState.logOpen}
      position={$appSettings?.ui?.log_panel_position}
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
</style>
