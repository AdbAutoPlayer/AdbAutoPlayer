<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import SchemaForm from "$lib/components/form/SchemaForm.svelte";
  import Menu from "$lib/components/menu/Menu.svelte";
  import { appSettings, debugLogLevelOverwrite, pollState } from "$lib/stores";
  import { showErrorToast } from "$lib/toast/toast-error";
  import { t } from "$lib/i18n/i18n";
  import type {
    AppSettings,
    MenuOption, Trigger,
  } from "$pytauri/_apiTypes";

  import { EventNames } from "$lib/log/eventNames";
  import type { MenuButton, ProfileProps, PydanticSettingsFormResponse, SettingsProps } from "$lib/menu/model";
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

  let profileProps: ProfileProps = $state({
    activeProfile: 0,
    states: []
  })

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
        isProcessRunning: "Debug" === (profileProps.states[profileProps.activeProfile]?.activeTask ?? null),
        option: {
          label: "Debug",
          args: [],
          category: "Settings, Phone & Debug",
        },
      },
    ];
  });
  let activeGameMenuButtons: MenuButton[] = $derived.by(() => {
    const profile = profileProps.activeProfile;
    const menuButtons: MenuButton[] = [...defaultButtons];

    const activeGame = profileProps.states[profile]?.activeGame ?? null;
    if (!activeGame) {
      return menuButtons;
    }

    const activeTask = profileProps.states[profile]?.activeTask ?? null;

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
          label: "Stop Action",
          args: [],
          tooltip: `Stops the currently running process`,
        },
      });
    }

    return menuButtons;
  });
  let categories: string[] = $derived.by(() => {
    const profile = profileProps.activeProfile;
    let tempCategories = ["Settings, Phone & Debug"];

    const activeGame = profileProps.states[profile]?.activeGame ?? null;
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
    clearTimeout(updateStateTimeout);

    await stopTask({profile_index: profile})
    if (profileProps.states[profile]) {
      profileProps.states[profile].activeTask = null;
    }

    updateStateTimeout = setTimeout(updateStateHandler, 1000);
  }
  async function callDebug() {
    const profile = profileProps.activeProfile;
    const task = profileProps.states[profile]?.activeTask ?? null;
    if (task !== null) {
      return;
    }

    $pollState = false;

    try {
      if (profileProps.states[profile]) {
        profileProps.states[profile].activeTask = "Debug";
      }
      $debugLogLevelOverwrite = true;
      await debug({profile_index: profile});
    } catch (error) {
      await showErrorToast(error, { title: `Failed to Start: Debug` });
    }

    $debugLogLevelOverwrite = false;
    enablePolling();
  }
  async function callStartTask(menuOption: MenuOption) {
    const profile = profileProps.activeProfile;
    const task = profileProps.states[profile]?.activeTask ?? null;
    if (task !== null) {
      return;
    }

    try {
      const taskPromise = startTask({
        profile_index: profile,
        args: menuOption.args,
        label: menuOption.label
      });
      await updateState();
      await taskPromise;
    } catch (error) {
      await showErrorToast(error, { title: `Failed to Start: ${menuOption.label}` });
    }
  }
  async function onFormSubmit() {
    const profile = profileProps.activeProfile;
    clearTimeout(updateStateTimeout);
    // console.log($state.snapshot(settingsProps));
    try {
      if (settingsProps.fileName === "App.toml") {
        const newSettings: AppSettings = await invoke("save_app_settings", {
          settings: settingsProps.formData
        })
        await applySettings(newSettings)
        const profileCount = $appSettings?.profiles?.profiles?.length ?? 1;
        if (profileCount >= profileProps.activeProfile) {
          profileProps.activeProfile = profileCount - 1;
        }

        profileProps.states.forEach((value, index) => {
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
      await logError(String(e))
    }
    updateStateTimeout = setTimeout(updateStateHandler, 1000);
    settingsProps = {
      showSettingsForm: false,
      formData: {},
      formSchema: {},
      fileName: "",
    }
    enablePolling();
    return;
  }
  async function openGameSettingsForm(game: GameGUIOptions | null) {
    if (game === null) {
      await showErrorToast("Failed to Open Game Settings: No game found");
      return;
    }

    const profile = profileProps.activeProfile;

    $pollState = false;
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
      enablePolling()
    }
  }
  async function openAdbSettingsForm() {
    const profile = profileProps.activeProfile;
    $pollState = false;
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
      enablePolling();
    }
  }

  // State logic probably needs to stay here but needs to be refactored on per
  // profile basis, current polling logic does not work.
  let updateStateTimeout: number | undefined;
  async function updateStateHandler() {
    try {
      await updateState();
      updateStateTimeout = setTimeout(updateStateHandler, 3000);
    } catch (error) {
      await showErrorToast(error, { title: "Failed to connect to Device" });
      updateStateTimeout = setTimeout(updateStateHandler, 30000);
    }
  }

  async function updateState() {
    const profile = profileProps.activeProfile;
    const profileCount = $appSettings?.profiles?.profiles?.length ?? 1;

    if (!$pollState) {
      return;
    }
    const state = await getProfileState({
      profile_index: profile,
    });
    // console.log($state.snapshot(state));

    profileProps.states[profile] = {
      activeGame: state.game_menu,
      activeTask: state.active_task,
      deviceId: state.device_id,
    }

    for (let i = 0; i < profileCount; i++) {
      if (!$pollState) {
        return;
      }
      if (i === profile) continue;

      const otherState = await getProfileState({
        profile_index: i,
      });

      profileProps.states[i] = {
        activeGame: otherState.game_menu,
        activeTask:  otherState.active_task,
        deviceId: state.device_id,
      }
    }
  }

  function enablePolling() {
    $pollState = true;
    if (profileProps.states[profileProps.activeProfile]) {
      profileProps.states[profileProps.activeProfile].activeTask = null;
    }
  }

  onMount(() => {
    enablePolling();
    updateStateHandler();
  });

  onDestroy(() => {
    clearTimeout(updateStateTimeout);
  });
</script>

{#if !settingsProps.showSettingsForm && $pollState }
  <ProfileSelector
    bind:profileProps={profileProps}
    bind:settingsProps={settingsProps}
  />
{/if}

<main class="w-full pt-2 pr-4 pb-4 pl-4">
  <h1 class="pb-2 text-center h1 text-3xl select-none">
    {$t(profileProps.states[profileProps.activeProfile]?.activeGame?.game_title || "Start any supported Game!")}
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
          disableActions={Boolean(profileProps.states[profileProps.activeProfile]?.activeTask)}
          {categories}
        />
      {/if}
    </div>
  </div>
</main>

<aside class="flex min-h-6 flex-grow flex-col pr-4 pb-4 pl-4">
  <ActiveLogDisplayCard profileIndex={profileProps.activeProfile} />
</aside>
