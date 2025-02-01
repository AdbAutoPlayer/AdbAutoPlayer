<script lang="ts">
  import {
    GetEditableMainConfig,
    SaveMainConfig,
    GetRunningSupportedGame,
    GetEditableGameConfig,
    SaveAFKJourneyConfig,
    StartGameProcess,
    TerminateGameProcess,
    IsGameProcessRunning,
  } from "$lib/wailsjs/go/main/App";
  import { LogError } from "$lib/wailsjs/runtime";
  import { onDestroy, onMount } from "svelte";
  import CommandPanel from "./CommandPanel.svelte";
  import ConfigForm from "./ConfigForm.svelte";
  import Menu from "./Menu.svelte";
  import { logoAwake } from "$lib/stores/logo";
  import { afkjourney, config, games } from "$lib/wailsjs/go/models";
  const defaultButtons: MenuButton[] = [
    {
      label: "Edit Main Config",
      callback: () => openMainConfigForm(),
      active: false,
    },
  ];

  let showConfigForm: boolean = $state(false);
  let configFormProps: Record<string, any> = $state({});
  let activeGame: games.Game | null = $state(null);

  let openFormIsMainConfig: boolean = $state(false);

  let configSaveCallback: (config: object) => void = $derived.by(() => {
    if (openFormIsMainConfig) {
      return onMainConfigSave;
    }
    if (activeGame?.GameTitle == "AFK Journey") {
      return onAFKJourneyConfigSave;
    }
    return function () {
      LogError("Not Implemented");
    };
  });

  let activeGameMenuButtons: MenuButton[] = $derived.by(() => {
    if (activeGame?.MenuOptions && activeGame.MenuOptions.length > 0) {
      const menuButtons: MenuButton[] = activeGame.MenuOptions.map(
        (menuOption) => ({
          label: menuOption.Label,
          callback: (event) =>
            startGameProcess(event, activeGame, menuOption.Args),
          active: false,
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

  function startGameProcess(
    event: PointerEvent,
    game: games.Game | null,
    args: string[],
  ) {
    if (game === null) {
      return;
    }
    const target = event.target as HTMLElement;

    activeGameMenuButtons.forEach((button) => {
      button.active = button.label === target.textContent;
    });
    $logoAwake = false;
    StartGameProcess(game, args).catch((err) => {
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

  function onAFKJourneyConfigSave(configObject: object) {
    if (activeGame?.GameTitle !== "AFK Journey") {
      return;
    }
    SaveAFKJourneyConfig(activeGame, afkjourney.Config.createFrom(configObject))
      .catch((err) => {
        alert(err);
      })
      .finally(() => {
        showConfigForm = false;
        $logoAwake = true;
      });
  }

  function openGameConfigForm(game: games.Game | null) {
    if (game === null) {
      return;
    }
    openFormIsMainConfig = false;
    $logoAwake = false;
    GetEditableGameConfig(game)
      .then((result) => {
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
    if (!$logoAwake) {
      IsGameProcessRunning().then((response: boolean) => {
        $logoAwake = !response;
      });
    } else {
      GetRunningSupportedGame()
        .then((game) => {
          activeGame = game;
        })
        .catch((err) => {
          console.log(err);
          activeGame = null;
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
    {activeGame?.GameTitle ?? "Please start a supported game"}
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
