<script lang="ts">
  import {
    GetEditableMainConfig,
    SaveMainConfig,
    GetRunningSupportedGame,
    GetEditableGameConfig,
    SaveGameConfig,
    StartGameProcess,
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

  let showConfigForm: boolean = $state(false);
  let configFormProps: Record<string, any> = $state({});
  let activeGame: ipc.GameGUI | null = $state(null);
  let logGetRunningSupportedGame: boolean = $state(true);

  let openFormIsMainConfig: boolean = $state(false);

  let configSaveCallback: (config: object) => void = $derived.by(() => {
    if (openFormIsMainConfig) {
      return onMainConfigSave;
    }

    return onGameConfigSave;
  });

  let activeButtonLabel: string | null = $state(null);

  let defaultButtons: MenuButton[] = $derived.by(() => {
    return [
      {
        callback: () => openMainConfigForm(),
        isProcessRunning: false,
        option: ipc.MenuOption.createFrom({
          label: "Edit Main Config",
          category: "Config",
          tooltip:
            "Global settings that apply to the app as a whole, not specific to any game.",
        }),
      },
      {
        callback: () =>
          startGameProcess({
            label: "Set Display Size 1080x1920",
            args: ["WMSize1080x1920"],
          }),
        isProcessRunning: "Set Display Size 1080x1920" === activeButtonLabel,
        option: ipc.MenuOption.createFrom({
          label: "Set Display Size 1080x1920",
          category: "Phone",
        }),
      },
      {
        callback: () =>
          startGameProcess({
            label: "Reset Display Size",
            args: ["WMSizeReset"],
          }),
        isProcessRunning: "Reset Display Size" === activeButtonLabel,
        option: ipc.MenuOption.createFrom({
          label: "Reset Display Size",
          category: "Phone",
        }),
      },
    ];
  });

  let activeGameMenuButtons: MenuButton[] = $derived.by(() => {
    if (activeGame?.menu_options && activeGame.menu_options.length > 0) {
      const menuButtons: MenuButton[] = activeGame.menu_options.map(
        (menuOption) => ({
          callback: () => startGameProcess(menuOption),
          isProcessRunning: menuOption.label === activeButtonLabel,
          option: menuOption,
        }),
      );
      menuButtons.push(...defaultButtons);
      menuButtons.push(
        {
          callback: () => openGameConfigForm(activeGame),
          isProcessRunning: false,
          option: ipc.MenuOption.createFrom({
            label: `Edit ${activeGame.game_title} Config`,
            category: "Config",
          }),
        },
        {
          callback: () => stopGameProcess(),
          isProcessRunning: false,
          alwaysEnabled: true,
          option: ipc.MenuOption.createFrom({
            label: "Stop Action",
            tooltip: `Stops the currently running process`,
          }),
        },
      );

      return menuButtons;
    }
    return defaultButtons;
  });

  let categories: string[] = $derived.by(() => {
    let tempCategories = ["Config", "Phone"];
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
    try {
      await TerminateGameProcess();
      activeButtonLabel = null;
    } catch (error) {
      console.error(error);
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
      activeButtonLabel = menuOption.label;
    } catch (error) {
      console.error(error);

      alert(error);
    }
    setTimeout(updateStateHandler, 1000);
  }

  async function onMainConfigSave(configObject: object) {
    console.log("onMainConfigSave");
    const configForm = config.MainConfig.createFrom(configObject);
    console.log(configForm);

    try {
      await SaveMainConfig(configForm);
    } catch (error) {
      console.error(error);
      alert(error);
    }

    showConfigForm = false;
    logGetRunningSupportedGame = true;
    $pollRunningGame = true;
    $pollRunningProcess = true;
  }

  async function onGameConfigSave(configObject: object) {
    if (!activeGame) {
      return;
    }

    try {
      await SaveGameConfig(configObject);
    } catch (error) {
      console.error(error);
      alert(error);
    }

    showConfigForm = false;
    $pollRunningGame = true;
    $pollRunningProcess = true;
  }

  async function openGameConfigForm(game: ipc.GameGUI | null) {
    console.log("openGameConfigForm");
    if (game === null) {
      console.log("game === null");
      return;
    }
    $pollRunningGame = false;
    $pollRunningProcess = false;

    openFormIsMainConfig = false;
    try {
      const result = await GetEditableGameConfig(game);
      console.log(result);
      result.constraints = sortObjectByOrder(result.constraints);
      configFormProps = result;
      showConfigForm = true;
    } catch (error) {
      console.error(error);
      alert(error);
      $pollRunningGame = true;
      $pollRunningProcess = true;
    }
  }

  async function openMainConfigForm() {
    openFormIsMainConfig = true;
    $pollRunningGame = false;
    $pollRunningProcess = false;
    try {
      const result = await GetEditableMainConfig();
      result.constraints = sortObjectByOrder(result.constraints);
      configFormProps = result;
      showConfigForm = true;
    } catch (error) {
      console.error(error);
      alert(error);
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
  {activeGame?.game_title ?? "Start any supported Game!"}
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
