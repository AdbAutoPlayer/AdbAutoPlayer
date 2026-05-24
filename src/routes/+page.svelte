<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import { profiles, settings, ui } from "$lib/stores.svelte";
  import { showErrorToast } from "$lib/toast/toast-error";
  import { t } from "$lib/i18n/i18n";
  import type { MenuOption } from "$pytauri/_apiTypes";

  import type { MenuButton } from "$lib/menu/model";
  import {
    debug,
    getProfileState,
    startTask,
    stopTask,
  } from "$pytauri/apiClient";
  import Hero from "$lib/components/modern/Hero.svelte";
  import TaskGrid from "$lib/components/modern/TaskGrid.svelte";

  const currentProfileState = $derived(profiles.states[profiles.active]);

  // Used for the current display.
  let defaultButtons: MenuButton[] = $derived([]);

  let activeGameMenuButtons: MenuButton[] = $derived.by(() => {
    const menuButtons: MenuButton[] = [...defaultButtons];

    const gameMenu = currentProfileState?.game_menu ?? null;
    if (!gameMenu) {
      return menuButtons;
    }

    const activeTask = currentProfileState?.active_task ?? null;

    if (gameMenu?.menu_options) {
      menuButtons.push(
        ...gameMenu.menu_options
          .filter(
            (opt) =>
              opt.label !== "Stop Task" && !opt.label.includes("Display Size"),
          )
          .map((menuOption) => ({
            callback: () => callStartTask(menuOption),
            isProcessRunning: menuOption.label === activeTask,
            option: {
              ...menuOption,
              label: menuOption.custom_label ?? menuOption.label,
            },
          })),
      );

      // Game Settings card removed - accessible via global UI
    }

    return menuButtons;
  });

  let categories: string[] = $derived.by(() => {
    let tempCategories = ["Settings, Phone & Debug"];

    const gameMenu = currentProfileState?.game_menu ?? null;
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
      profiles.setTimestamp(Date.now() / 1000 + 0.5);
      if (profiles.states[profile]) {
        profiles.states[profile].active_task = null;
        profiles.setStates([...profiles.states]);
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
    const profile = profiles.active;
    const task = profiles.states[profile]?.active_task ?? null;
    if (task !== null) {
      return;
    }

    try {
      if (profiles.states[profile]) {
        profiles.states[profile].active_task = "Debug";
        profiles.setStates([...profiles.states]);
      }
      await debug({ profile_index: profile });
    } catch (error) {
      void showErrorToast(error, {
        title: `Failed to Start: Debug`,
        profile: profile,
      });
    }

    void getProfileState({
      profile_index: profile,
    });
  }

  async function callStartTask(menuOption: MenuOption) {
    const profile = profiles.active;
    const task = profiles.states[profile]?.active_task ?? null;
    if (task !== null) {
      return;
    }
    profiles.setTimestamp(Date.now() / 1000 + 5.0);
    if (profiles.states[profile]) {
      profiles.states[profile].active_task = menuOption.label;
      profiles.setStates([...profiles.states]);
    }

    try {
      const taskPromise = startTask({
        profile_index: profile,
        args: menuOption.args,
        label: menuOption.label,
      });
      await taskPromise;
    } catch (error) {
      profiles.setTimestamp(Date.now() + 1000);
      await showErrorToast(error, {
        title: `Failed to Start: ${menuOption.label}`,
      });
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
      console.error(error);
    }
    updateStateTimeout = setTimeout(handleStateUpdate, 3000);
  }

  async function updateState(profile: number | null = null) {
    const profileCount = settings.settings?.profiles?.profiles?.length ?? 1;
    if (profile !== null) {
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
    window.addEventListener("trigger-state-update", () => triggerStateUpdate());
    void triggerStateUpdate();
  });

  onDestroy(() => {
    clearTimeout(updateStateTimeout);
  });
</script>

<div class="page-content">
  <Hero
    onStop={() => callStopTask(profiles.active)}
    activeTaskButton={activeGameMenuButtons.find((b) => b.isProcessRunning)}
  />

  <div class="task-view">
    <TaskGrid
      buttons={activeGameMenuButtons}
      disableActions={Boolean(profiles.states[profiles.active]?.active_task)}
      {categories}
    />
  </div>
</div>

<style>
  .page-content {
    display: flex;
    flex-direction: column;
    height: 100%;
    position: relative;
  }

  .task-view {
    flex: 1;
    min-height: 0;
  }
</style>
