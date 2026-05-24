<script lang="ts">
  import { Dialog, Portal } from "@skeletonlabs/skeleton-svelte";
  import IconX from "$lib/components/icons/feather/IconX.svelte";
  import { t } from "$lib/i18n/i18n";
  import { invoke } from "@tauri-apps/api/core";
  import { showErrorToast } from "$lib/toast/toast-error";
  import { settings, profiles } from "$lib/stores.svelte";
  import type {
    RustSettingsFormResponse,
    SettingsProps,
  } from "$lib/menu/model";
  import Menu from "$lib/components/icons/lucide/Menu.svelte";
  import { applySettings } from "$lib/utils/settings";
  import type { AppSettings } from "$pytauri/_apiTypes";

  let {
    settingsProps = $bindable(),
  }: {
    settingsProps: SettingsProps;
  } = $props();

  async function openAppSettingsForm() {
    try {
      const data: RustSettingsFormResponse = await invoke(
        "get_app_settings_form",
      );
      // console.log(data);

      settingsProps = {
        showSettingsForm: true,
        formData: data.settings,
        formSchema: JSON.parse(data.schema),
        fileName: data.file_name,
      };
      // console.log($state.snapshot(settingsProps));
    } catch (error) {
      await showErrorToast(error, {
        title: "Failed to create App Settings Form",
      });
    }
  }

  function getProfiles(): string[] {
    return settings.settings?.profiles?.profiles ?? ["Default"];
  }

  function getDeviceID(profile: number): string {
    if (profiles.states[profile] && profiles.states[profile].device_id) {
      return ` (${profiles.states[profile].device_id})`;
    }

    return " (Offline)";
  }

  function getStatus(profile: number): string {
    if (!profiles.states[profile] || !profiles.states[profile].device_id) {
      return "";
    }

    if (!profiles.states[profile].game_menu?.game_title) {
      return "Idle";
    }

    const gameTitle = profiles.states[profile].game_menu.game_title;

    if (!profiles.states[profile].active_task) {
      return `${gameTitle} - Idle`;
    }

    const activeTask = profiles.states[profile].active_task;

    return `${gameTitle} — ${activeTask}`;
  }

  function getStatusColor(profile: number): string {
    if (!profiles.states[profile] || !profiles.states[profile].device_id) {
      return "bg-gray-500";
    }
    if (
      !profiles.states[profile].game_menu?.game_title ||
      !profiles.states[profile].active_task
    ) {
      return "bg-yellow-500";
    }

    return "bg-green-500";
  }

  async function selectProfile(index: number) {
    if (!settings.settings) return;
    profiles.select(index);

    try {
      const newSettings = {
        ...settings.settings,
        profiles: { ...settings.settings.profiles, active_profile: index },
      };
      const savedSettings: AppSettings = await invoke("save_app_settings", {
        settings: newSettings,
      });
      await applySettings(savedSettings);
    } catch (e) {
      console.error("Failed to save active profile:", e);
    }
  }
</script>

<Dialog>
  <Dialog.Trigger
    class="btn fixed top-0 left-0 z-50 m-2 cursor-pointer select-none"
  >
    <Menu size={24} />
  </Dialog.Trigger>
  <Portal>
    <Dialog.Backdrop
      class="bg-surface-50-950/50 fixed inset-0 z-50 opacity-0 transition transition-discrete data-[state=open]:opacity-100 starting:data-[state=open]:opacity-0"
    />
    <Dialog.Positioner class="fixed inset-0 z-50 flex justify-start">
      <Dialog.Content
        class="card bg-surface-100-900 flex h-screen w-sm -translate-x-full flex-col p-4 opacity-0 shadow-xl transition transition-discrete data-[state=open]:translate-x-0 data-[state=open]:opacity-100 starting:data-[state=open]:-translate-x-full starting:data-[state=open]:opacity-0"
      >
        <!-- Header -->
        <header class="mb-4 flex items-center justify-between">
          <Dialog.Title class="text-2xl font-bold"
            >{$t("Profiles")}</Dialog.Title
          >
          <Dialog.CloseTrigger class="btn-icon hover:preset-tonal">
            <IconX size={16} />
          </Dialog.CloseTrigger>
        </header>

        <!-- Profile list -->
        <aside class="flex-1 space-y-2 overflow-y-auto">
          {#each getProfiles() as profile, i}
            <button
              class="btn preset-tonal flex w-full items-center justify-start rounded {i ===
              profiles.active
                ? 'preset-outlined'
                : ''} transition-colors"
              class:selected={i === profiles.active}
              onclick={() => selectProfile(i)}
            >
              <span class={`h-3 w-3 rounded-full ${getStatusColor(i)}`}></span>

              <span class="text-left whitespace-normal">
                <span class="font-semibold">{profile} {getDeviceID(i)}</span>
                <br />
                <span class="text-sm opacity-80">{getStatus(i)}</span>
              </span>
            </button>
          {/each}
        </aside>

        <!-- Sticky footer -->
        <footer class="bg-surface-100-900 sticky bottom-0 mt-4 py-2">
          <button
            class="btn-primary btn preset-tonal-primary w-full p-2"
            onclick={() => openAppSettingsForm()}
          >
            Settings
          </button>
        </footer>
      </Dialog.Content>
    </Dialog.Positioner>
  </Portal>
</Dialog>
