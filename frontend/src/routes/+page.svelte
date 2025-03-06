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
  import ConfigForm from "./ConfigForm.svelte";
  import Menu from "./Menu.svelte";
  import { pollRunningGame, pollRunningProcess } from "$lib/stores/polling";
  import { config, ipc } from "$lib/wailsjs/go/models";
  import { sortObjectByOrder } from "$lib/orderHelper";

  let showConfigForm: boolean = $state(false);
  let configFormProps: Record<string, any> = $state({});
  let activeGame: ipc.GameGUI | null = $state(null);

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
        label: "Edit Main Config",
        callback: () => openMainConfigForm(),
        active: false,
      },
      {
        label: "Reset Display Size",
        callback: () =>
          startGameProcess({
            label: "Reset Display Size",
            args: ["WMSizeReset"],
          }),
        active: "Reset Display Size" === activeButtonLabel,
      },
    ];
  });

  let activeGameMenuButtons: MenuButton[] = $derived.by(() => {
    if (activeGame?.menu_options && activeGame.menu_options.length > 0) {
      const menuButtons: MenuButton[] = activeGame.menu_options.map(
        (menuOption) => ({
          label: menuOption.label,
          callback: () => startGameProcess(menuOption),
          active: menuOption.label === activeButtonLabel,
          alwaysEnabled: false,
        }),
      );
      menuButtons.push(
        {
          label: "Edit Main Config",
          callback: () => openMainConfigForm(),
          active: false,
          alwaysEnabled: false,
        },
        {
          label: "Reset Display Size",
          callback: () =>
            startGameProcess({
              label: "Reset Display Size",
              args: ["WMSizeReset"],
            }),
          active: "Reset Display Size" === activeButtonLabel,
        },
        {
          label: "Edit Game Config",
          callback: () => openGameConfigForm(activeGame),
          active: false,
          alwaysEnabled: false,
        },
        {
          label: "Stop Action",
          callback: () => stopGameProcess(),
          active: false,
          alwaysEnabled: true,
        },
      );

      return menuButtons;
    }
    return [];
  });

  async function stopGameProcess() {
    clearTimeout(updateStateTimeout);
    try {
      await TerminateGameProcess();
    } catch (error) {
      console.log(error);
    }
    setTimeout(updateStateHandler, 1000);
    activeButtonLabel = null;
  }

  async function startGameProcess(menuOption: ipc.MenuOption) {
    activeButtonLabel = menuOption.label;
    clearTimeout(updateStateTimeout);

    try {
      await StartGameProcess(menuOption.args);
    } catch (error) {
      console.log(error);
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
      console.log(error);
      alert(error);
    }

    showConfigForm = false;
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
      console.log(error);
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
      console.log(error);
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
        const response = await IsGameProcessRunning();
        $pollRunningGame = !response;
        if ($pollRunningGame) {
          activeButtonLabel = null;
        }
      }
    } catch (err) {
      console.log(`err: ${err}`);
    }

    try {
      if ($pollRunningGame) {
        activeGame = await GetRunningSupportedGame();
      }
    } catch (err) {
      console.log(`err: ${err}`);
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

<h1 class="text-3xl text-center pb-4">
  {activeGame?.game_title ?? "Start any supported Game!"}
</h1>
<div
  class="card p-4 bg-surface-100-900/50 border-[1px] border-surface-200-800 text-center flex flex-col max-h-[60vh] overflow-hidden"
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
      buttons={activeGameMenuButtons ?? []}
      {defaultButtons}
      disableActions={!$pollRunningGame}
    ></Menu>
  {/if}
</div>
