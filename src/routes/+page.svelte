<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import SchemaForm from "$lib/components/form/SchemaForm.svelte";
  import Menu from "$lib/components/menu/Menu.svelte";
  import { appSettings, debugLogLevelOverwrite, profileStore } from "$lib/stores";
  import { showErrorToast } from "$lib/toast/toast-error";
  import { t } from "$lib/i18n/i18n";
  import type {
    AppSettings,
    MenuOption, Trigger,
  } from "$pytauri/_apiTypes";

  import { EventNames } from "$lib/log/eventNames";
  import type { MenuButton, PydanticSettingsFormResponse, SettingsProps } from "$lib/menu/model";
  import type { GameGUIOptions } from "$pytauri/_apiTypes";
  import {
    cacheClear,
    debug,
    getAdbSettingsForm,
    getProfileState,
    getGameSettingsForm,
    startTask,
    stopTask,
  } from "$pytauri/apiClient";
  import { invoke } from "@tauri-apps/api/core";
  import { logError } from "$lib/log/log-events";
  import ActiveLogDisplayCard from "$lib/components/log/ActiveLogDisplayCard.svelte";
  import ProfileSelector from "$lib/components/menu/ProfileSelector.svelte";
  import { applySettings } from "$lib/utils/settings";

  let settingsProps: SettingsProps = $state({
    showSettingsForm: false,
    formData: {},
    formSchema: {},
    fileName: "",
  });
  // Used for the current display.
  let defaultButtons: MenuButton[] = $derived.by(() => {
    return [
      {
        callback: () => openAdbSettingsForm(),
        isProcessRunning: false,
        option: {
          label: "ADB Settings",
          args: [],
          category: "Settings, Phone & Debug",
          tooltip:
            "Global settings-form that apply to the app as a whole, not specific to any game.",
        },
      },
      {
        callback: () => callDebug(),
        isProcessRunning: "Debug" === ($profileStore.states[$profileStore.activeProfile]?.activeTask ?? null),
        option: {
          label: "Debug",
          args: [],
          category: "Settings, Phone & Debug",
        },
      },
    ];
  });
  let activeGameMenuButtons: MenuButton[] = $derived.by(() => {
    const profile = $profileStore.activeProfile;
    const menuButtons: MenuButton[] = [...defaultButtons];

    const activeGame = $profileStore.states[profile]?.activeGame ?? null;
    if (!activeGame) {
      return menuButtons;
    }

    const activeTask = $profileStore.states[profile]?.activeTask ?? null;

    if (activeGame?.menu_options) {
      menuButtons.push(
        ...activeGame.menu_options.map((menuOption) => ({
          callback: () => callStartTask(menuOption),
          isProcessRunning: menuOption.label === activeTask,
          option: menuOption,
        })),
      );

      if (activeGame.settings_file) {
        menuButtons.push({
          callback: () => openGameSettingsForm(activeGame),
          isProcessRunning: false,
          option: {
            // This one needs to be translated because of the params
            label: $t("{{game}} Settings", {
              game: activeGame.game_title
                ? $t(activeGame.game_title)
                : $t("Game"),
            }),
            args: [],
            category: "Settings, Phone & Debug",
          },
        });
      }

      menuButtons.push({
        callback: () => callStopTask(profile),
        isProcessRunning: false,
        alwaysEnabled: true,
        option: {
          label: "Stop Task",
          args: [],
          tooltip: `Stops the currently running Task`,
        },
      });
    }

    return menuButtons;
  });
  let categories: string[] = $derived.by(() => {
    const profile = $profileStore.activeProfile;
    let tempCategories = ["Settings, Phone & Debug"];

    const activeGame = $profileStore.states[profile]?.activeGame ?? null;
    if (!activeGame) {
      return tempCategories;
    }

    if (activeGame.categories) {
      tempCategories.push(...activeGame.categories);
    }

    if (activeGame.menu_options && activeGame.menu_options.length > 0) {
      activeGame.menu_options.forEach((menuOption) => {
        if (menuOption.category) {
          tempCategories.push(menuOption.category);
        }
      });
    }

    return Array.from(new Set(tempCategories));
  });

  async function callStopTask(profile: number) {
    stopStateUpdates();

    try {
      await stopTask({profile_index: profile})
      if ($profileStore.states[profile]) {
        $profileStore.states[profile].activeTask = null;
      }
    } catch (error) {
      void showErrorToast(error, {
        logToLogDisplay: false,
        profile: profile,
      })
    }

    await triggerStateUpdate();
  }
  async function callDebug() {
    const profile = $profileStore.activeProfile;
    const task = $profileStore.states[profile]?.activeTask ?? null;
    if (task !== null) {
      return;
    }

    stopStateUpdates();

    try {
      if ($profileStore.states[profile]) {
        $profileStore.states[profile].activeTask = "Debug";
      }
      $debugLogLevelOverwrite = true;
      await debug({profile_index: profile});
    } catch (error) {
      void showErrorToast(error, { title: `Failed to Start: Debug`, profile: profile, });
    }

    $debugLogLevelOverwrite = false;
    await triggerStateUpdate();
  }
  async function callStartTask(menuOption: MenuOption) {
    const profile = $profileStore.activeProfile;
    const task = $profileStore.states[profile]?.activeTask ?? null;
    if (task !== null) {
      return;
    }

    if ($profileStore.states[profile]) {
      $profileStore.states[profile].activeTask = menuOption.label;
    }

    try {
      const taskPromise = startTask({
        profile_index: profile,
        args: menuOption.args,
        label: menuOption.label
      });
      await triggerStateUpdate();
      await taskPromise;
    } catch (error) {
      await showErrorToast(error, { title: `Failed to Start: ${menuOption.label}` });
    }
  }

  async function onFormSubmit() {
    stopStateUpdates(); // should not be needed but leaving it as is.
    const profile = $profileStore.activeProfile;
    // console.log($state.snapshot(settingsProps));
    try {
      if (settingsProps.fileName === "App.toml") {
        const newSettings: AppSettings = await invoke("save_app_settings", {
          settings: settingsProps.formData
        })
        await applySettings(newSettings)
        const profileCount = $appSettings?.profiles?.profiles?.length ?? 1;
        if (profileCount >= $profileStore.activeProfile) {
          $profileStore.activeProfile = profileCount - 1;
        }

        $profileStore.states.forEach((value, index) => {
          if (index >= profileCount) {
            callStopTask(index);
          }
        });
      } else {
        await invoke("save_settings", {
          profileIndex: profile,
          fileName: settingsProps.fileName,
          jsonData: JSON.stringify(settingsProps.formData)
        });
        if (settingsProps.fileName.endsWith("ADB.toml")) {
          await cacheClear({
            profile_index: profile,
            trigger: EventNames.ADB_SETTINGS_UPDATED as Trigger
          });
        } else {
          await cacheClear({
            profile_index: profile,
            trigger: EventNames.GAME_SETTINGS_UPDATED as Trigger
          });
        }
      }
    } catch (e) {
      void logError(String(e))
    }
    settingsProps = {
      showSettingsForm: false,
      formData: {},
      formSchema: {},
      fileName: "",
    }
    await triggerStateUpdate();
    return;
  }
  async function openGameSettingsForm(game: GameGUIOptions | null) {
    if (game === null) {
      void showErrorToast("Failed to Open Game Settings: No game found");
      return;
    }

    stopStateUpdates();
    const profile = $profileStore.activeProfile;

    try {
      const data = await getGameSettingsForm({
        profile_index: profile,
      }) as PydanticSettingsFormResponse;
      // console.log(data);

      settingsProps = {
        showSettingsForm: true,
        formData: data[0],
        formSchema: data[1],
        fileName: data[2],
      }
    } catch (error) {
      await showErrorToast(error, {
        title: "Failed to create Game Settings Form",
      });
      await triggerStateUpdate();
    }
  }
  async function openAdbSettingsForm() {
    stopStateUpdates();
    const profile = $profileStore.activeProfile;
    try {
      const data = await getAdbSettingsForm({profile_index: profile})  as PydanticSettingsFormResponse;
      // console.log(data);

      settingsProps = {
        showSettingsForm: true,
        formData: data[0],
        formSchema: data[1],
        fileName: data[2],
      }
    } catch (error) {
      await showErrorToast(error, {
        title: "Failed to create ADB Settings Form",
      });
      await triggerStateUpdate();
    }
  }

  let updateStateTimeout: number | undefined;
  function stopStateUpdates() {
    clearTimeout(updateStateTimeout);
  }
  async function triggerStateUpdate() {
    clearTimeout(updateStateTimeout);
    await handleStateUpdate();
  }
  async function handleStateUpdate() {
    try {
      await updateState();
    } catch (error) {
      // Should not happen
      console.error(error);
    }

    updateStateTimeout = setTimeout(handleStateUpdate, 3000);
  }

  // Function is not using recursion intentionally
  // Recursion does not play too nicely with Svelte reactivity.
  // TODO completely refactor this into an event listener.
  // State update events should be dispatched from Backend to make this
  // less blocking...
  // Implementation was fine for single instance but really kills
  // responsiveness in multi instance
  async function updateState() {
    const profile = $profileStore.activeProfile;
    const profileCount = $appSettings?.profiles?.profiles?.length ?? 1;

    try {
      const state = await getProfileState({
        profile_index: profile,
      });

      $profileStore.states[profile] = {
        activeGame: state.game_menu,
        activeTask: state.active_task,
        deviceId: state.device_id,
      }
    } catch (e) {
      if ($profileStore.states[profile]?.activeTask) {
        void callStopTask(profile)
      }
      $profileStore.states[profile] = {
        activeGame: null,
        activeTask: null,
        deviceId: null,
      }
    }

    for (let i = 0; i < profileCount; i++) {
      if (i === profile) continue;

      try {
        const otherState = await getProfileState({
          profile_index: i,
        });

        $profileStore.states[i] = {
          activeGame: otherState.game_menu,
          activeTask:  otherState.active_task,
          deviceId: otherState.device_id,
        }
      } catch (e) {
        if ($profileStore.states[i]?.activeTask) {
          void callStopTask(i)
        }
        $profileStore.states[i] = {
          activeGame: null,
           activeTask: null,
          deviceId: null,
        }
      }
    }
  }

  onMount(() => {
    void triggerStateUpdate();
  });

  onDestroy(() => {
    stopStateUpdates();
  });
</script>

{#if !settingsProps.showSettingsForm }
  <ProfileSelector
    bind:settingsProps={settingsProps}
  />
{/if}

<main class="w-full pt-2 pr-4 pb-4 pl-4">
  <h1 class="pb-2 text-center h1 text-3xl select-none">
    {$t($profileStore.states[$profileStore.activeProfile]?.activeGame?.game_title || "Start any supported Game!")}
  </h1>
  <div
    class="flex max-h-[70vh] min-h-[20vh] flex-col overflow-hidden card bg-surface-100-900/50 p-4 text-center select-none"
  >
    <div
      class="flex-grow overflow-y-scroll pr-4"
    >
      {#if settingsProps.showSettingsForm}
        <SchemaForm bind:settingsProps={settingsProps} {onFormSubmit} />
      {:else}
        <Menu
          buttons={activeGameMenuButtons}
          disableActions={Boolean($profileStore.states[$profileStore.activeProfile]?.activeTask)}
          {categories}
        />
      {/if}
    </div>
  </div>
</main>

<aside class="flex min-h-6 flex-grow flex-col pr-4 pb-4 pl-4">
  <ActiveLogDisplayCard profileIndex={$profileStore.activeProfile} />
</aside>
