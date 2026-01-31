<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import SchemaForm from "$lib/form/SchemaForm.svelte";
  import Menu from "$lib/components/menu/Menu.svelte";
  import {
    activeProfile,
    appSettings,
    debugLogLevelOverwrite,
    profileStates,
    profileStateTimestamp,
  } from "$lib/stores";
  import { showErrorToast } from "$lib/toast/toast-error";
  import { t } from "$lib/i18n/i18n";
  import type {
    AppSettings,
    GameGUIOptions,
    MenuOption,
    Trigger,
  } from "$pytauri/_apiTypes";

  import { EventNames } from "$lib/log/eventNames";
  import type {
    MenuButton,
    PydanticSettingsFormResponse,
    SettingsProps,
  } from "$lib/menu/model";
  import {
    cacheClear,
    debug,
    getAdbSettingsForm,
    getGameSettingsForm,
    getProfileState,
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
        isProcessRunning:
          "Debug" === ($profileStates[$activeProfile]?.active_task ?? null),
        option: {
          label: "Debug",
          args: [],
          category: "Settings, Phone & Debug",
        },
      },
    ];
  });
  let activeGameMenuButtons: MenuButton[] = $derived.by(() => {
    const profile = $activeProfile;
    const menuButtons: MenuButton[] = [...defaultButtons];

    const gameMenu = $profileStates[profile]?.game_menu ?? null;
    if (!gameMenu) {
      return menuButtons;
    }

    const activeTask = $profileStates[profile]?.active_task ?? null;

    if (gameMenu?.menu_options) {
      menuButtons.push(
        ...gameMenu.menu_options.map((menuOption) => ({
          callback: () => callStartTask(menuOption),
          isProcessRunning: menuOption.label === activeTask,
          option: menuOption,
        })),
      );

      if (gameMenu.settings_file) {
        menuButtons.push({
          callback: () => openGameSettingsForm(gameMenu),
          isProcessRunning: false,
          option: {
            // This one needs to be translated because of the params
            label: $t("{{game}} Settings", {
              game: gameMenu.game_title ? $t(gameMenu.game_title) : $t("Game"),
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
    const profile = $activeProfile;
    let tempCategories = ["Settings, Phone & Debug"];

    const gameMenu = $profileStates[profile]?.game_menu ?? null;
    if (!gameMenu) {
      return tempCategories;
    }

    if (gameMenu.categories) {
      tempCategories.push(...gameMenu.categories);
    }

    if (gameMenu.menu_options && gameMenu.menu_options.length > 0) {
      gameMenu.menu_options.forEach((menuOption) => {
        if (menuOption.category) {
          tempCategories.push(menuOption.category);
        }
      });
    }

    return Array.from(new Set(tempCategories));
  });

  async function callStopTask(profile: number) {
    try {
      await stopTask({ profile_index: profile });
      $profileStateTimestamp = Date.now() + 500;
      if ($profileStates[profile]) {
        $profileStates[profile].active_task = null;
      }
    } catch (error) {
      void showErrorToast(error, {
        logToLogDisplay: false,
        profile: profile,
      });
    }
    void getProfileState({
      profile_index: profile,
    });
  }
  async function callDebug() {
    const profile = $activeProfile;
    const task = $profileStates[profile]?.active_task ?? null;
    if (task !== null) {
      return;
    }

    try {
      if ($profileStates[profile]) {
        $profileStates[profile].active_task = "Debug";
      }
      $debugLogLevelOverwrite[profile] = true;
      await debug({ profile_index: profile });
    } catch (error) {
      void showErrorToast(error, {
        title: `Failed to Start: Debug`,
        profile: profile,
      });
    }

    $debugLogLevelOverwrite[profile] = false;
    void getProfileState({
      profile_index: profile,
    });
  }
  async function callStartTask(menuOption: MenuOption) {
    const profile = $activeProfile;
    const task = $profileStates[profile]?.active_task ?? null;
    if (task !== null) {
      return;
    }
    $profileStateTimestamp = Date.now() + 5000;
    if ($profileStates[profile]) {
      $profileStates[profile].active_task = menuOption.label;
    }

    try {
      const taskPromise = startTask({
        profile_index: profile,
        args: menuOption.args,
        label: menuOption.label,
      });
      $profileStateTimestamp = Date.now() + 2500;
      await taskPromise;
    } catch (error) {
      $profileStateTimestamp = Date.now() + 1000;
      await showErrorToast(error, {
        title: `Failed to Start: ${menuOption.label}`,
      });
    }
  }

  async function onFormSubmit() {
    const profile = $activeProfile;
    // console.log($state.snapshot(settingsProps));
    try {
      if (settingsProps.fileName === "App.toml") {
        const newSettings: AppSettings = await invoke("save_app_settings", {
          settings: settingsProps.formData,
        });
        await applySettings(newSettings);
        const profileCount = $appSettings?.profiles?.profiles?.length ?? 1;
        if (profileCount >= $activeProfile) {
          $activeProfile = profileCount - 1;
        }

        $profileStates.forEach((value, index) => {
          if (index >= profileCount) {
            void callStopTask(index);
          }
        });
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
    settingsProps = {
      showSettingsForm: false,
      formData: {},
      formSchema: {},
      fileName: "",
    };
    await triggerStateUpdate();
    return;
  }
  async function openGameSettingsForm(game: GameGUIOptions | null) {
    if (game === null) {
      void showErrorToast("Failed to Open Game Settings: No game found");
      return;
    }

    clearTimeout(updateStateTimeout);
    try {
      const data = (await getGameSettingsForm({
        profile_index: $activeProfile,
      })) as PydanticSettingsFormResponse;
      // console.log(data);

      settingsProps = {
        showSettingsForm: true,
        formData: data[0],
        formSchema: data[1],
        fileName: data[2],
      };
    } catch (error) {
      await showErrorToast(error, {
        title: "Failed to create Game Settings Form",
      });
      await triggerStateUpdate();
    }
  }
  async function openAdbSettingsForm() {
    clearTimeout(updateStateTimeout);
    try {
      const data = (await getAdbSettingsForm({
        profile_index: $activeProfile,
      })) as PydanticSettingsFormResponse;
      // console.log(data);

      settingsProps = {
        showSettingsForm: true,
        formData: data[0],
        formSchema: data[1],
        fileName: data[2],
      };
    } catch (error) {
      await showErrorToast(error, {
        title: "Failed to create ADB Settings Form",
      });
      await triggerStateUpdate();
    }
  }

  let updateStateTimeout: ReturnType<typeof setTimeout> | undefined;

  async function triggerStateUpdate(profile: number | null = null) {
    clearTimeout(updateStateTimeout);
    await handleStateUpdate(profile);
  }
  async function handleStateUpdate(profile: number | null = null) {
    try {
      await updateState(profile);
    } catch (error) {
      // Should not happen
      console.error(error);
    }

    updateStateTimeout = setTimeout(handleStateUpdate, 3000);
  }

  async function updateState(profile: number | null = null) {
    const profileCount = $appSettings?.profiles?.profiles?.length ?? 1;

    if (profile) {
      void getProfileState({
        profile_index: profile,
      });
      return;
    }

    for (let i = 0; i < profileCount; i++) {
      void getProfileState({
        profile_index: i,
      });
    }
  }

  onMount(() => {
    void triggerStateUpdate();
  });

  onDestroy(() => {
    clearTimeout(updateStateTimeout);
  });
</script>

{#if !settingsProps.showSettingsForm}
  <ProfileSelector bind:settingsProps />
{/if}

<main class="w-full pt-2 pr-4 pb-4 pl-4">
  <h1 class="pb-2 text-center h1 text-3xl select-none">
    {$t(
      $profileStates[$activeProfile]?.game_menu?.game_title ||
        "Start any supported Game!",
    )}
  </h1>
  <div
    class="flex max-h-[70vh] min-h-[20vh] flex-col overflow-hidden card bg-surface-100-900/50 p-4 text-center select-none"
  >
    <div class="flex-grow overflow-y-scroll pr-4">
      {#if settingsProps.showSettingsForm}
        <SchemaForm bind:settingsProps {onFormSubmit} />
      {:else}
        <Menu
          buttons={activeGameMenuButtons}
          disableActions={Boolean($profileStates[$activeProfile]?.active_task)}
          {categories}
        />
      {/if}
    </div>
  </div>
</main>

<aside class="flex min-h-6 flex-grow flex-col pr-4 pb-4 pl-4">
  <ActiveLogDisplayCard profileIndex={$activeProfile} />
</aside>
