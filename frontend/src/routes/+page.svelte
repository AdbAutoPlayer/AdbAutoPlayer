<script lang="ts">
  import {
    GetEditableGeneralSettings,
    SaveGeneralSettings,
    GetRunningSupportedGame,
    GetEditableGameSettings,
    SaveGameSettings,
    StartGameProcess,
    Debug,
    SaveDebugZip,
    TerminateGameProcess,
    IsGameProcessRunning,
  } from "$lib/wailsjs/go/main/App";
  import { onDestroy, onMount } from "svelte";
  import ConfigForm from "./ConfigForm/ConfigForm.svelte";
  import Menu from "./Menu/Menu.svelte";
  import { pollRunningGame, pollRunningProcess } from "$lib/stores/polling";
  import { config, ipc } from "$lib/wailsjs/go/models";
  import { sortObjectByOrder } from "$lib/orderHelper";
  import type { MenuButton } from "$lib/model";
  import { showErrorToast } from "$lib/utils/error";
  import { t } from "$lib/i18n/i18n";
  import { applyUISettings } from "$lib/utils/settings";

  let showConfigForm: boolean = $state(false);
  let configFormProps: Record<string, any> = $state({});
  let activeGame: ipc.GameGUI | null = $state(null);
  let logGetRunningSupportedGame: boolean = $state(true);

  let openFormIsGeneralSettings: boolean = $state(false);

  let configSaveCallback: (config: object) => void = $derived.by(() => {
    if (openFormIsGeneralSettings) {
      return onGeneralSettingsSave;
    }

    return onGameSettingsSave;
  });

  let activeButtonLabel: string | null = $state(null);

  let defaultButtons: MenuButton[] = $derived.by(() => {
    return [
      {
        callback: () => openGeneralSettingsForm(),
        isProcessRunning: false,
        option: ipc.MenuOption.createFrom({
          label: "General Settings",
          category: "Settings, Phone & Debug",
          tooltip:
            "Global settings that apply to the app as a whole, not specific to any game.",
        }),
      },
      {
        callback: () => debug(),
        isProcessRunning: "Show Debug info" === activeButtonLabel,
        option: ipc.MenuOption.createFrom({
          label: "Show Debug info",
          category: "Settings, Phone & Debug",
        }),
      },
      {
        callback: () => SaveDebugZip(),
        isProcessRunning: false,
        option: ipc.MenuOption.createFrom({
          label: "Save debug.zip",
          category: "Settings, Phone & Debug",
        }),
      },
    ];
  });

  let activeGameMenuButtons: MenuButton[] = $derived.by(() => {
    const menuButtons: MenuButton[] = [...defaultButtons];

    if (activeGame?.menu_options) {
      menuButtons.push(
        ...activeGame.menu_options.map((menuOption) => ({
          callback: () => startGameProcess(menuOption),
          isProcessRunning: menuOption.label === activeButtonLabel,
          option: menuOption,
        })),
      );

      if (activeGame.config_path) {
        menuButtons.push({
          callback: () => openGameSettingsForm(activeGame),
          isProcessRunning: false,
          option: ipc.MenuOption.createFrom({
            // This one needs to be translated because of the params
            label: $t("{{game}} Settings", {
              game: activeGame.game_title
                ? $t(activeGame.game_title)
                : $t("Game"),
            }),
            category: "Settings, Phone & Debug",
          }),
        });
      }

      menuButtons.push({
        callback: () => stopGameProcess(),
        isProcessRunning: false,
        alwaysEnabled: true,
        option: ipc.MenuOption.createFrom({
          label: "Stop Action",
          tooltip: `Stops the currently running process`,
        }),
      });
    }

    return menuButtons;
  });

  let categories: string[] = $derived.by(() => {
    let tempCategories = ["Settings, Phone & Debug"];
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

  async function stopGameProcess() {
    clearTimeout(updateStateTimeout);

    await TerminateGameProcess();
    activeButtonLabel = null;

    setTimeout(updateStateHandler, 1000);
  }

  async function debug() {
    if (activeButtonLabel !== null) {
      return;
    }
    clearTimeout(updateStateTimeout);

    try {
      activeButtonLabel = "Show Debug info";
      await Debug();
    } catch (error) {
      showErrorToast(error, { title: "Failed to generate Debug Info" });
    }
    setTimeout(updateStateHandler, 1000);
  }

  async function startGameProcess(menuOption: ipc.MenuOption) {
    if (activeButtonLabel !== null) {
      return;
    }
    clearTimeout(updateStateTimeout);

    try {
      activeButtonLabel = menuOption.label;
      await StartGameProcess(menuOption.args);
    } catch (error) {
      showErrorToast(error, { title: `Failed to Start: ${menuOption.label}` });
    }
    setTimeout(updateStateHandler, 1000);
  }

  async function onGeneralSettingsSave(configObject: object) {
    console.log("onGeneralSettingsSave");
    const configForm = config.MainConfig.createFrom(configObject);

    try {
      await SaveGeneralSettings(configForm);
      applyUISettings(configForm["User Interface"]);
    } catch (error) {
      showErrorToast(error, { title: "Failed to Save General Settings" });
    }

    showConfigForm = false;
    logGetRunningSupportedGame = true;
    $pollRunningGame = true;
    $pollRunningProcess = true;
  }

  async function onGameSettingsSave(configObject: object) {
    const game = activeGame;
    if (!game) {
      return;
    }

    try {
      console.log("onGameSettingsSave", configObject);
      await SaveGameSettings(configObject);
      activeGame = await GetRunningSupportedGame(!logGetRunningSupportedGame);
    } catch (error) {
      showErrorToast(error, {
        title: `Failed to Save ${game.game_title} Settings`,
      });
    }

    showConfigForm = false;
    $pollRunningGame = true;
    $pollRunningProcess = true;
  }

  async function openGameSettingsForm(game: ipc.GameGUI | null) {
    console.log("openGameSettingsForm");
    if (game === null) {
      console.log("game === null");
      return;
    }
    $pollRunningGame = false;
    $pollRunningProcess = false;

    openFormIsGeneralSettings = false;
    try {
      const result = await GetEditableGameSettings(game);
      console.log(result);
      result.constraints = sortObjectByOrder(result.constraints);
      configFormProps = result;
      showConfigForm = true;
    } catch (error) {
      showErrorToast(error, {
        title: `Failed to create ${game.game_title} Settings Form`,
      });
      $pollRunningGame = true;
      $pollRunningProcess = true;
    }
  }

  async function openGeneralSettingsForm() {
    openFormIsGeneralSettings = true;
    $pollRunningGame = false;
    $pollRunningProcess = false;
    try {
      const result = await GetEditableGeneralSettings();
      result.constraints = sortObjectByOrder(result.constraints);
      configFormProps = result;
      showConfigForm = true;
    } catch (error) {
      showErrorToast(error, {
        title: "Failed to create General Settings Form",
      });
      $pollRunningGame = true;
      $pollRunningProcess = true;
    }
  }

  let updateStateTimeout: number | undefined;
  async function updateStateHandler() {
    await updateState();
    if (activeGame) {
      updateStateTimeout = setTimeout(updateStateHandler, 10000);
    } else {
      updateStateTimeout = setTimeout(updateStateHandler, 3000);
    }
  }

  async function updateState() {
    try {
      if ($pollRunningProcess) {
        const isProcessRunning = await IsGameProcessRunning();
        $pollRunningGame = !isProcessRunning;
        if (!isProcessRunning) {
          activeButtonLabel = null;
        }
      }
    } catch (error) {
      console.error(error);
    }

    try {
      if ($pollRunningGame) {
        activeGame = await GetRunningSupportedGame(!logGetRunningSupportedGame);
        logGetRunningSupportedGame = false;
      }
    } catch (error) {
      console.error(error);
      activeGame = null;
    }
  }

  onMount(() => {
    updateStateHandler();
  });

  onDestroy(() => {
    clearTimeout(updateStateTimeout);
  });
</script>

<h1 class="pb-4 text-center h1 text-3xl select-none">
  {$t(activeGame?.game_title || "Start any supported Game!")}
</h1>
<div
  class="flex max-h-[70vh] min-h-[20vh] flex-col overflow-hidden card bg-surface-100-900/50 p-4 text-center select-none"
>
  {#if showConfigForm}
    <div class="flex-grow overflow-y-scroll">
      <ConfigForm
        configObject={configFormProps.config ?? []}
        constraints={configFormProps.constraints ?? []}
        onConfigSave={configSaveCallback}
      />
    </div>
  {:else}
    <Menu
      buttons={activeGameMenuButtons}
      disableActions={!$pollRunningGame}
      {categories}
    ></Menu>
  {/if}
</div>
