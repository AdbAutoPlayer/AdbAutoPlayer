<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import SettingsForm from "$lib/components/settings/SettingsForm.svelte";
  import Menu from "$lib/components/menu/Menu.svelte";
  import { pollRunningGame } from "$lib/stores/polling";
  import { sortObjectByOrder } from "$lib/settings-form/orderHelper";
  import { showErrorToast } from "$lib/toast/toast-error";
  import { t } from "$lib/i18n/i18n";
  import {
    GetGeneralSettingsForm,
    SaveGeneralSettings,
  } from "@wails/settings/settingsservice";
  import { GeneralSettings } from "@wails/settings";
  import {
    Debug,
    GetGameGUI,
    GetGameSettingsForm,
    SaveDebugZip,
    SaveGameSettings,
    StartGameProcess,
    KillGameProcess,
  } from "@wails/games/gamesservice";
  import { GameGUI, MenuOption } from "@wails/ipc";
  import type { MenuButton } from "$lib/settings-form/model";
  import { Events } from "@wailsio/runtime";
  import { EventNames } from "$lib/log/eventNames";
  import { resetScrollOnStateChange } from "$lib/attachments/resetScrollOnStateChange";

  let showSettingsForm: boolean = $state(false);
  let settingsFormSettings: Record<string, any> = $state({});
  let settingsFormConstraints: Record<string, any> = $state({});

  let activeGame: GameGUI | null = $state(null);

  let openFormIsGeneralSettings: boolean = $state(false);

  let settingsSaveCallback: (settings: object) => void = $derived.by(() => {
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
        option: MenuOption.createFrom({
          label: "General Settings",
          category: "Settings, Phone & Debug",
          tooltip:
            "Global settings-form that apply to the app as a whole, not specific to any game.",
        }),
      },
      {
        callback: () => debug(),
        isProcessRunning: "Show Debug info" === activeButtonLabel,
        option: MenuOption.createFrom({
          label: "Show Debug info",
          category: "Settings, Phone & Debug",
        }),
      },
      {
        callback: () => SaveDebugZip(),
        isProcessRunning: false,
        option: MenuOption.createFrom({
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
          option: MenuOption.createFrom({
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
        option: MenuOption.createFrom({
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

    await KillGameProcess();
    activeButtonLabel = null;

    updateStateTimeout = setTimeout(updateStateHandler, 1000);
  }

  async function debug() {
    if (activeButtonLabel !== null) {
      return;
    }

    $pollRunningGame = false;
    clearTimeout(updateStateTimeout);

    try {
      activeButtonLabel = "Show Debug info";
      await Debug();
    } catch (error) {
      showErrorToast(error, { title: `Failed to Start: Show Debug info` });
    }
    updateStateTimeout = setTimeout(updateStateHandler, 1000);
  }

  async function startGameProcess(menuOption: MenuOption) {
    if (activeButtonLabel !== null) {
      return;
    }
    $pollRunningGame = false;
    clearTimeout(updateStateTimeout);

    try {
      activeButtonLabel = menuOption.label;
      await StartGameProcess(menuOption.args);
    } catch (error) {
      showErrorToast(error, { title: `Failed to Start: ${menuOption.label}` });
    }
    updateStateTimeout = setTimeout(updateStateHandler, 1000);
  }

  async function onGeneralSettingsSave(settings: object) {
    clearTimeout(updateStateTimeout);
    const settingsForm = GeneralSettings.createFrom(settings);

    try {
      await SaveGeneralSettings(settingsForm);
    } catch (error) {
      showErrorToast(error, { title: "Failed to Save General Settings" });
    }

    updateStateTimeout = setTimeout(updateStateHandler, 1000);
    showSettingsForm = false;
  }

  async function onGameSettingsSave(settings: object) {
    const game = activeGame;
    if (!game) {
      return;
    }

    try {
      activeGame = await SaveGameSettings(settings);
    } catch (error) {
      showErrorToast(error, {
        title: `Failed to Save ${game.game_title} Settings`,
      });
    }

    showSettingsForm = false;
  }

  async function openGameSettingsForm(game: GameGUI | null) {
    if (game === null) {
      showErrorToast("Failed to Open Game Settings: No game found");
      return;
    }

    $pollRunningGame = false;

    openFormIsGeneralSettings = false;
    try {
      const result = await GetGameSettingsForm(game);
      settingsFormSettings = result.settings;
      settingsFormConstraints = sortObjectByOrder(result.constraints);

      showSettingsForm = true;
    } catch (error) {
      showErrorToast(error, {
        title: `Failed to create ${game.game_title} Settings Form`,
      });
      $pollRunningGame = true;
    }
  }

  async function openGeneralSettingsForm() {
    openFormIsGeneralSettings = true;
    $pollRunningGame = false;
    try {
      const result = await GetGeneralSettingsForm();
      settingsFormSettings = result.settings;
      settingsFormConstraints = sortObjectByOrder(result.constraints);
      showSettingsForm = true;
    } catch (error) {
      showErrorToast(error, {
        title: "Failed to create General Settings Form",
      });
      $pollRunningGame = true;
    }
  }

  let updateStateTimeout: number | undefined;
  async function updateStateHandler() {
    try {
      await updateState();
      updateStateTimeout = setTimeout(updateStateHandler, 3000);
    } catch (error) {
      showErrorToast(error, { title: "Failed to connect to Device" });
      updateStateTimeout = setTimeout(updateStateHandler, 30000);
    }
  }

  async function updateState() {
    if (!$pollRunningGame) {
      return;
    }

    activeGame = await GetGameGUI();
  }

  onMount(() => {
    function enablePolling() {
      $pollRunningGame = true;
      activeButtonLabel = null;
    }

    const unsubTaskStoped = Events.On(EventNames.TASK_STOPPED, enablePolling);
    const unsubGameSettingsUpdated = Events.On(
      EventNames.GAME_SETTINGS_UPDATED,
      enablePolling,
    );
    const unsubGeneralSettingsUpdated = Events.On(
      EventNames.GENERAL_SETTINGS_UPDATED,
      enablePolling,
    );

    return () => {
      unsubTaskStoped();
      unsubGameSettingsUpdated();
      unsubGeneralSettingsUpdated();
    };
  });

  onMount(() => {
    updateStateHandler();
  });

  onDestroy(() => {
    clearTimeout(updateStateTimeout);
  });
</script>

<h1 class="pb-2 text-center h1 text-3xl select-none">
  {$t(activeGame?.game_title || "Start any supported Game!")}
</h1>
<div
  class="flex max-h-[70vh] min-h-[20vh] flex-col overflow-hidden card bg-surface-100-900/50 p-4 text-center select-none"
>
  <div
    {@attach resetScrollOnStateChange(showSettingsForm)}
    class="flex-grow overflow-y-scroll pr-4"
  >
    {#if showSettingsForm}
      <SettingsForm
        settings={settingsFormSettings}
        constraints={settingsFormConstraints}
        onSettingsSave={settingsSaveCallback}
      />
    {:else}
      <Menu
        buttons={activeGameMenuButtons}
        disableActions={!$pollRunningGame}
        {categories}
      />
    {/if}
  </div>
</div>
