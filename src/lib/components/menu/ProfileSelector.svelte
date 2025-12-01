<script lang="ts">
  import { Dialog, Portal } from "@skeletonlabs/skeleton-svelte";
  import IconX from "$lib/components/icons/feather/IconX.svelte";
  import { t } from "$lib/i18n/i18n";
  import { invoke } from "@tauri-apps/api/core";
  import { showErrorToast } from "$lib/toast/toast-error";
  import { appSettings, profileStates, activeProfile } from "$lib/stores";
  import type {
    RustSettingsFormResponse,
    SettingsProps,
  } from "$lib/menu/model";
  import Menu from "$lib/components/icons/lucide/Menu.svelte";

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
    return $appSettings?.profiles?.profiles ?? ["Default"];
  }

  function getDeviceID(profile: number): string {
    if ($profileStates[profile] && $profileStates[profile].device_id) {
      return ` (${$profileStates[profile].device_id})`;
    }

    return " (Offline)";
  }

  function getStatus(profile: number): string {
    if (!$profileStates[profile] || !$profileStates[profile].device_id) {
      return "";
    }

    if (!$profileStates[profile].game_menu?.game_title) {
      return "Idle";
    }

    const gameTitle = $profileStates[profile].game_menu.game_title;

    if (!$profileStates[profile].active_task) {
      return `${gameTitle} - Idle`;
    }

    const activeTask = $profileStates[profile].active_task;

    return `${gameTitle} — ${activeTask}`;
  }

  function getStatusColor(profile: number): string {
    if (!$profileStates[profile] || !$profileStates[profile].device_id) {
      return "bg-gray-500";
    }
    if (
      !$profileStates[profile].game_menu?.game_title ||
      !$profileStates[profile].active_task
    ) {
      return "bg-yellow-500";
    }

    return "bg-green-500";
  }

  function selectProfile(index: number) {
    $activeProfile = index;
  }
</script>

<Dialog>
  <Dialog.Trigger
    class="fixed top-0 left-0 z-50 m-2 btn cursor-pointer select-none"
  >
    <Menu size={24} />
  </Dialog.Trigger>
  <Portal>
    <Dialog.Backdrop
      class="fixed inset-0 z-50 bg-surface-50-950/50 opacity-0 transition transition-discrete data-[state=open]:opacity-100 starting:data-[state=open]:opacity-0"
    />
    <Dialog.Positioner class="fixed inset-0 z-50 flex justify-start">
      <Dialog.Content
        class="flex h-screen w-sm -translate-x-full flex-col card bg-surface-100-900 p-4 opacity-0 shadow-xl transition transition-discrete data-[state=open]:translate-x-0 data-[state=open]:opacity-100 starting:data-[state=open]:-translate-x-full starting:data-[state=open]:opacity-0"
      >
        <!-- Header -->
        <header class="mb-4 flex items-center justify-between">
          <Dialog.Title class="text-2xl font-bold"
            >{$t("Profiles")}</Dialog.Title
          >
          <Dialog.CloseTrigger class="btn-icon preset-tonal">
            <IconX size={16} />
          </Dialog.CloseTrigger>
        </header>

        <!-- Profile list -->
        <aside class="flex-1 space-y-2 overflow-y-auto">
          {#each getProfiles() as profile, i}
            <button
              class="btn flex w-full items-center justify-start rounded preset-outlined-primary-500 transition-colors"
              class:selected={i === $activeProfile}
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
        <footer class="sticky bottom-0 mt-4 bg-surface-100-900 py-2">
          <button
            class="btn-primary btn w-full preset-filled-primary-100-900 p-2 hover:preset-filled-primary-500"
            onclick={() => openAppSettingsForm()}
          >
            Settings
          </button>
        </footer>
      </Dialog.Content>
    </Dialog.Positioner>
  </Portal>
</Dialog>
