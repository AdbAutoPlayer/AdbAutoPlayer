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
  import CommandPanel from "./CommandPanel.svelte";
  import ConfigForm from "./ConfigForm.svelte";
  import Menu from "./Menu.svelte";
  import { logoAwake } from "$lib/stores/logo";
  import { config, ipc } from "$lib/wailsjs/go/models";
  import { sortObjectByOrder } from "$lib/orderHelper";
  const defaultButtons: MenuButton[] = [
    {
      label: "Edit Main Config",
      callback: () => openMainConfigForm(),
      active: false,
    },
  ];

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
          label: "Edit Game Config",
          callback: () => openGameConfigForm(activeGame),
          active: false,
          alwaysEnabled: false,
        },
        {
          label: "Stop Action",
          callback: () => TerminateGameProcess(),
          active: false,
          alwaysEnabled: true,
        },
      );

      return menuButtons;
    }
    return [];
  });

  function startGameProcess(menuOption: ipc.MenuOption) {
    activeButtonLabel = menuOption.label;

    $logoAwake = false;
    StartGameProcess(menuOption.args).catch((err) => {
      console.log(err);
      alert(err);
    });
  }

  function onMainConfigSave(configObject: object) {
    SaveMainConfig(config.MainConfig.createFrom(configObject))
      .catch((err) => {
        alert(err);
      })
      .finally(() => {
        showConfigForm = false;
        $logoAwake = true;
      });
  }

  function onGameConfigSave(configObject: object) {
    if (!activeGame) {
      return;
    }
    SaveGameConfig(configObject)
      .catch((err) => {
        alert(err);
      })
      .finally(() => {
        showConfigForm = false;
        $logoAwake = true;
      });
  }

  function openGameConfigForm(game: ipc.GameGUI | null) {
    if (game === null) {
      return;
    }
    openFormIsMainConfig = false;
    $logoAwake = false;
    GetEditableGameConfig(game)
      .then((result) => {
        result.constraints = sortObjectByOrder(result.constraints);
        configFormProps = result;
        showConfigForm = true;
      })
      .catch((err) => {
        $logoAwake = true;
        alert(err);
      });
  }

  function openMainConfigForm() {
    openFormIsMainConfig = true;
    $logoAwake = false;
    GetEditableMainConfig()
      .then((result) => {
        result.constraints = sortObjectByOrder(result.constraints);
        configFormProps = result;
        showConfigForm = true;
      })
      .catch((err) => {
        $logoAwake = true;
        alert(err);
      });
  }

  let updateStateTimeout: number | undefined;
  function updateState() {
    if (showConfigForm) {
      updateStateTimeout = setTimeout(updateState, 2500);
      return;
    }

    IsGameProcessRunning()
      .then((response: boolean) => {
        $logoAwake = !response;
      })
      .catch((err) => {
        console.log(err);
        updateStateTimeout = setTimeout(updateState, 2500);
      });

    if ($logoAwake) {
      GetRunningSupportedGame()
        .then((game) => {
          activeGame = game;
        })
        .catch((err) => {
          console.log(err);
          activeGame = null;
          updateStateTimeout = setTimeout(updateState, 2500);
        });
    }
    updateStateTimeout = setTimeout(updateState, 2500);
  }

  onMount(() => {
    updateState();
  });

  onDestroy(() => {
    clearTimeout(updateStateTimeout);
  });
</script>

<main class="container no-select">
  <h1>
    {activeGame?.game_title ?? "Loading"}
  </h1>
  {#if showConfigForm}
    <CommandPanel title={"Config"}>
      <ConfigForm
        configObject={configFormProps.config ?? []}
        constraints={configFormProps.constraints ?? []}
        onConfigSave={configSaveCallback}
      />
    </CommandPanel>
  {:else}
    <CommandPanel title={"Menu"}>
      <Menu
        buttons={activeGameMenuButtons ?? []}
        {defaultButtons}
        disableActions={!$logoAwake}
      ></Menu>
    </CommandPanel>
  {/if}
</main>

<style>
  .container {
    margin: 0;
    padding-top: 0;
    display: flex;
    flex-direction: column;
  }
</style>
