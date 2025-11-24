<script lang="ts">
  import { Dialog, Portal } from '@skeletonlabs/skeleton-svelte';
  import IconX from "$lib/components/icons/feather/IconX.svelte";
  import { t } from "$lib/i18n/i18n";
  import { invoke } from "@tauri-apps/api/core";
  import { showErrorToast } from "$lib/toast/toast-error";
  import { appSettings, profileStore } from "$lib/stores";
  import type { RustSettingsFormResponse, SettingsProps } from "$lib/menu/model";
  import Menu from "$lib/components/icons/lucide/Menu.svelte";

  let {
    settingsProps = $bindable(),
  }: {
    settingsProps: SettingsProps;
  } = $props();

  async function openAppSettingsForm() {
    try {
      const data: RustSettingsFormResponse = await invoke("get_app_settings_form");
      // console.log(data);

      settingsProps = {
        showSettingsForm: true,
        formData: data.settings,
        formSchema: JSON.parse(data.schema),
        fileName: data.file_name,
      }
      // console.log($state.snapshot(settingsProps));
    } catch (error) {
      await showErrorToast(error, {
        title: "Failed to create App Settings Form",
      });
    }
  }

  function getProfiles(): string[] {
    return $appSettings?.profiles?.profiles  ?? ["Default"]
  }

  function getDeviceID(profile: number): string {
    if ($profileStore.states[profile] && $profileStore.states[profile].deviceId) {
      return ` (${$profileStore.states[profile].deviceId})`;
    }

    return " (Offline)";
  }

  function getStatus(profile: number): string {
    if (!$profileStore.states[profile] || !$profileStore.states[profile].deviceId) {
      return "";
    }

    if (!$profileStore.states[profile].activeGame?.game_title) {
      return "Idle";
    }

    const gameTitle = $profileStore.states[profile].activeGame.game_title;

    if (!$profileStore.states[profile].activeTask) {
      return `${gameTitle} - Idle`
    }

    const activeTask = $profileStore.states[profile].activeTask;

    return `${gameTitle} — ${activeTask}`;
  }

  function getStatusColor(profile: number): string {
    if (!$profileStore.states[profile] || !$profileStore.states[profile].deviceId) {
      return "bg-gray-500";
    }
    if (
      !$profileStore.states[profile].activeGame?.game_title
      || !$profileStore.states[profile].activeTask
    ) {
      return "bg-yellow-500";
    }

    return "bg-green-500";
  }

  function selectProfile(index: number) {
    $profileStore.activeProfile = index;
  }
</script>

<Dialog>
  <Dialog.Trigger class="btn fixed top-0 left-0 z-50 m-2 cursor-pointer select-none">
    <Menu size={24}/>
  </Dialog.Trigger>
  <Portal>
    <Dialog.Backdrop class="fixed inset-0 z-50 bg-surface-50-950/50 transition transition-discrete opacity-0 starting:data-[state=open]:opacity-0 data-[state=open]:opacity-100" />
    <Dialog.Positioner class="fixed inset-0 z-50 flex justify-start">
      <Dialog.Content class="h-screen card bg-surface-100-900 w-sm p-4 flex flex-col shadow-xl transition transition-discrete opacity-0 -translate-x-full starting:data-[state=open]:opacity-0 starting:data-[state=open]:-translate-x-full data-[state=open]:opacity-100 data-[state=open]:translate-x-0">

        <!-- Header -->
        <header class="flex justify-between items-center mb-4">
          <Dialog.Title class="text-2xl font-bold">{$t("Profiles")}</Dialog.Title>
          <Dialog.CloseTrigger class="btn-icon preset-tonal">
            <IconX size={16} />
          </Dialog.CloseTrigger>
        </header>

        <!-- Profile list -->
        <aside class="flex-1 overflow-y-auto space-y-2">
          {#each getProfiles() as profile, i}
            <button
              class="btn preset-outlined-primary-500 w-full flex items-center justify-start rounded transition-colors"
              class:selected={i === $profileStore.activeProfile}
              onclick={() => selectProfile(i)}
            >
              <span class={`w-3 h-3 rounded-full ${getStatusColor(i)}`}></span>

              <span class="text-left whitespace-normal">
                <span class="font-semibold">{profile} {getDeviceID(i)}</span>
                <br />
                <span class="text-sm opacity-80">{getStatus(i)}</span>
              </span>
            </button>
          {/each}
        </aside>

        <!-- Sticky footer -->
        <footer class="mt-4 sticky bottom-0 bg-surface-100-900 py-2">
          <button
            class="w-full p-2 btn btn-primary preset-filled-primary-100-900 hover:preset-filled-primary-500"
            onclick={() => openAppSettingsForm()}
          >
            Settings
          </button>
        </footer>

      </Dialog.Content>
    </Dialog.Positioner>
  </Portal>
</Dialog>
