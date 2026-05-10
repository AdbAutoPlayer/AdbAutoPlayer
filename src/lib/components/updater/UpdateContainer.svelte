<script lang="ts">
  import { check, Update } from "@tauri-apps/plugin-updater";
  import { Progress } from "@skeletonlabs/skeleton-svelte";
  import { onDestroy, onMount } from "svelte";
  import Download from "$lib/components/icons/lucide/Download.svelte";
  import { Dialog, Portal } from "@skeletonlabs/skeleton-svelte";
  import IconX from "$lib/components/icons/feather/IconX.svelte";
  import { t } from "$lib/i18n/i18n";
  import { emit } from "@tauri-apps/api/event";
  import { appSettings } from "$lib/stores";
  import { get } from "svelte/store";
  import { toaster } from "$lib/toast/toaster-svelte";

  let checkUpdateTimeout: ReturnType<typeof setTimeout> | undefined;
  let update: Update | null = $state(null);

  // Modal
  let isUpdating: boolean = $state(false);
  let isDialogOpen: boolean = $state(true);

  // Download
  let totalSize: number = $state(0);
  let downloaded: number = $state(0);
  let downloadProgress: number = $state(0);

  async function checkUpdate() {
    if (isUpdating) {
      return;
    }
    try {
      const firstUpdateDetected = update === null;
      update = await check({ timeout: 5000 });
      if (update && firstUpdateDetected) {
        isDialogOpen = true;

        const settings = get(appSettings);
        if (settings?.notifications?.desktop_notifications) {
          toaster.info({
            title: get(t)("Update Available"),
            description: get(t)(
              "A new version of AdbAutoPlayer is ready to install.",
            ),
          });
        }
      }
    } catch (e) {
      console.error(e);
    }

    checkUpdateTimeout = setTimeout(checkUpdate, 1000 * 60 * 15); // wait 15 minutes;
  }

  async function startUpdate(): Promise<void> {
    update = (await check({ timeout: 5000 })) ?? update;
    if (!update) {
      return;
    }

    isUpdating = true;

    await update.downloadAndInstall((event) => {
      switch (event.event) {
        case "Started":
          totalSize = event.data.contentLength ?? 0;
          downloaded = 0;
          downloadProgress = 0;
          break;

        case "Progress":
          downloaded += event.data.chunkLength;
          if (totalSize > 0) {
            downloadProgress = (downloaded / totalSize) * 100;
          }
          break;

        case "Finished":
          downloadProgress = 100;
          emit("kill-python")
            .then(() => {
              console.log("Kill signal sent to Python.");
            })
            .catch((err) => {
              console.error("Failed to send kill signal:", err);
            });
          break;
      }
    });
  }

  onMount(() => {
    // Only check for updates if we are running in a Tauri environment
    if ((window as any).__TAURI_INTERNALS__) {
      checkUpdateTimeout = setTimeout(checkUpdate, 500);
    }
  });

  onDestroy(() => {
    clearTimeout(checkUpdateTimeout);
  });
</script>

{#if update}
  <Dialog
    closeOnInteractOutside={false}
    open={isDialogOpen}
    onOpenChange={(details) => (isDialogOpen = details.open)}
  >
    <Dialog.Trigger
      class="fixed top-0 right-8 z-50 m-2 cursor-pointer transition-transform select-none hover:scale-110 active:scale-95 {isUpdating
        ? 'text-primary-500 animate-pulse'
        : 'text-text-3 hover:text-accent-hi'}"
    >
      <Download size={22} strokeWidth={2.5} />
    </Dialog.Trigger>
    <Portal>
      <Dialog.Backdrop
        class="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
      />
      <Dialog.Positioner
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <Dialog.Content
          class="modern-dialog bg-surface-100-900/80 relative w-full max-w-xl overflow-hidden rounded-2xl border border-white/10 p-0 shadow-2xl backdrop-blur-xl transition-all duration-300"
        >
          <!-- Decorative Background Gradient -->
          <div
            class="bg-accent/20 absolute -top-24 -right-24 h-48 w-48 rounded-full blur-3xl"
          ></div>
          <div
            class="bg-primary-500/10 absolute -bottom-24 -left-24 h-48 w-48 rounded-full blur-3xl"
          ></div>

          <div class="relative z-10 flex flex-col">
            <header
              class="flex items-center justify-between border-b border-white/5 p-6"
            >
              <div class="flex items-center gap-3">
                <div
                  class="bg-accent/10 text-accent-hi flex h-10 w-10 items-center justify-center rounded-xl"
                >
                  <Download size={20} />
                </div>
                <div>
                  <Dialog.Title class="text-xl font-bold tracking-tight">
                    {!isUpdating ? $t("Update Available") : $t("Updating...")}
                  </Dialog.Title>
                  <div class="text-text-4 text-xs font-medium">
                    {$t("Version")}
                    <span class="text-accent-hi">{update?.version}</span>
                  </div>
                </div>
              </div>
              <Dialog.CloseTrigger
                class="text-text-4 hover:text-text-1 rounded-lg p-2 transition-colors hover:bg-white/10"
              >
                <IconX size={18} />
              </Dialog.CloseTrigger>
            </header>

            <main
              class="max-h-[70vh] scrollbar-thin scrollbar-thumb-white/10 overflow-y-auto p-6"
            >
              {#if !isUpdating}
                <div class="space-y-6">
                  <p class="text-text-2 text-base leading-relaxed">
                    {$t(
                      "A new version of AdbAutoPlayer is ready. It's recommended to update for the latest features and fixes.",
                    )}
                  </p>

                  {#if update?.body}
                    <div class="space-y-3">
                      <div class="flex items-center gap-2">
                        <span class="bg-accent h-1 w-4 rounded-full"></span>
                        <span
                          class="text-text-3 text-xs font-bold tracking-widest uppercase"
                        >
                          {$t("Changelog")}
                        </span>
                      </div>
                      <div
                        class="rounded-xl border border-white/5 bg-black/40 p-5 shadow-inner"
                      >
                        <div
                          class="changelog-content text-text-3 text-sm leading-relaxed whitespace-pre-wrap"
                        >
                          {update.body}
                        </div>
                      </div>
                    </div>
                  {/if}
                </div>
              {:else}
                <div
                  class="flex flex-col items-center justify-center space-y-6 py-8"
                >
                  <div
                    class="relative flex h-32 w-32 items-center justify-center"
                  >
                    <!-- Rotating background ring -->
                    <div
                      class="animate-spin-slow border-accent/30 absolute inset-0 rounded-full border-2 border-dashed"
                    ></div>

                    <Progress
                      value={Math.round(downloadProgress)}
                      max={100}
                      class="progress-modern"
                    >
                      <div
                        class="absolute inset-0 flex flex-col items-center justify-center"
                      >
                        <span
                          class="text-accent-hi text-2xl font-bold tracking-tighter"
                        >
                          {Math.round(downloadProgress)}%
                        </span>
                        <span
                          class="text-text-4 text-[10px] font-bold tracking-widest uppercase"
                        >
                          {$t("progress")}
                        </span>
                      </div>
                      <Progress.Circle class="text-accent stroke-[6px]">
                        <Progress.CircleTrack class="stroke-white/5" />
                        <Progress.CircleRange
                          class="transition-all duration-500 ease-out"
                        />
                      </Progress.Circle>
                    </Progress>
                  </div>

                  <div class="text-center">
                    <p class="text-text-2 text-sm font-medium">
                      {$t("Downloading update...")}
                    </p>
                    <p class="text-text-4 mt-1 text-xs italic">
                      {$t("The App will restart automatically.")}
                    </p>
                  </div>
                </div>
              {/if}
            </main>

            {#if !isUpdating}
              <footer
                class="bg-surface-100-900/40 flex gap-3 border-t border-white/5 p-6"
              >
                <button
                  class="text-text-2 flex-1 rounded-xl bg-white/5 py-3 text-sm font-bold transition-all hover:bg-white/10 active:scale-95"
                  onclick={() => (isDialogOpen = false)}
                >
                  {$t("Later")}
                </button>
                <button
                  class="bg-accent hover:bg-accent-hi flex-[2] rounded-xl py-3 text-sm font-bold text-black transition-all hover:shadow-[0_0_20px_rgba(var(--accent-rgb),0.4)] active:scale-95"
                  onclick={startUpdate}
                >
                  {$t("Update Now")}
                </button>
              </footer>
            {/if}
          </div>
        </Dialog.Content>
      </Dialog.Positioner>
    </Portal>
  </Dialog>
{/if}

<style>
  :global(.progress-modern) {
    --progress-circle-size: 110px;
  }

  :global(.modern-dialog) {
    animation: dialogAppear 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  }

  @keyframes dialogAppear {
    from {
      opacity: 0;
      transform: scale(0.95) translateY(10px);
    }
    to {
      opacity: 1;
      transform: scale(1) translateY(0);
    }
  }

  .changelog-content {
    scrollbar-gutter: stable;
  }

  .animate-spin-slow {
    animation: spin 8s linear infinite;
  }

  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }

  /* Custom scrollbar for changelog */
  main::-webkit-scrollbar {
    width: 4px;
  }
  main::-webkit-scrollbar-track {
    background: transparent;
  }
  main::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 10px;
  }
  main::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.2);
  }
</style>
