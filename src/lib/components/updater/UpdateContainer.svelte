<script lang="ts">
  import { check, Update } from "@tauri-apps/plugin-updater";
  import { Progress } from "@skeletonlabs/skeleton-svelte";
  import { onDestroy, onMount } from "svelte";
  import Download from "$lib/components/icons/lucide/Download.svelte";
  import { Dialog, Portal } from "@skeletonlabs/skeleton-svelte";
  import IconX from "$lib/components/icons/feather/IconX.svelte";
  import { t } from "$lib/i18n/i18n";

  let checkUpdateTimeout: number | null = null;
  let update: Update | null = $state(null);

  // Modal
  let isUpdating: boolean = $state(false);
  let isDialogOpen: boolean = $state(true);

  // Download
  let totalSize = 0;
  let downloaded = 0;
  let downloadProgress: number = $state(0);

  async function checkUpdate() {
    if (isUpdating) {
      return;
    }
    try {
      const firstUpdateDetected = update === null;
      update = await check({timeout: 5000});
      if (update && firstUpdateDetected) {
        isDialogOpen = true;
      }
    } catch (e) {
      console.error(e);
    }

    checkUpdateTimeout = setTimeout(checkUpdate, 1000*60*15) // wait 15 minutes;
  }

  function startUpdate(): void {
    if (!update) {
      return;
    }
    isUpdating = true;
    update.downloadAndInstall((event) => {
      switch (event.event) {
        case 'Started':
          totalSize = event.data.contentLength ?? 0;
          downloaded = 0;
          downloadProgress = 0;
          break;

        case 'Progress':
          downloaded += event.data.chunkLength;
          if (totalSize > 0) {
            downloadProgress = (downloaded / totalSize) * 100;
          }
          break;

        case 'Finished':
          downloadProgress = 100;
          break;
      }
    });
  }

  onMount(() => {
    checkUpdateTimeout = setTimeout(checkUpdate, 500);
  })

  onDestroy(() => {
    checkUpdateTimeout = null;
  })
</script>

{#if update}
  <Dialog closeOnInteractOutside={false} open={isDialogOpen} onOpenChange={(details) => isDialogOpen = details.open}>
    <Dialog.Trigger class="fixed top-0 right-8 z-50 m-2 cursor-pointer select-none {isUpdating ? "text-primary-300" : ""}">
      <Download size={24} strokeWidth={2} />
    </Dialog.Trigger>
    <Portal>
      <Dialog.Backdrop class="fixed inset-0 z-50 bg-surface-50-950/50" />
      <Dialog.Positioner class="fixed inset-0 z-50 flex justify-center items-center p-4">
        <Dialog.Content class="card bg-surface-100-900 w-full max-w-xl p-4 space-y-4 shadow-xl transition transition-discrete opacity-0 translate-y-[100px] starting:data-[state=open]:opacity-0 starting:data-[state=open]:translate-y-[100px] data-[state=open]:opacity-100 data-[state=open]:translate-y-0">
          <header class="flex justify-between items-center mb-4">
            {#if !isUpdating}
              <Dialog.Title class="text-2xl font-bold">{$t("Update")}</Dialog.Title>
            {:else}
              <Dialog.Title class="text-2xl font-bold">{$t("The App will restart automatically.")}</Dialog.Title>
            {/if}
            <Dialog.CloseTrigger class="btn-icon preset-tonal">
              <IconX size={16} />
            </Dialog.CloseTrigger>
          </header>


          {#if !isUpdating}
            <footer class="mt-4 sticky bottom-0 bg-surface-100-900 py-2">
              <button
                class="w-full p-2 btn btn-primary preset-filled-primary-100-900 hover:preset-filled-primary-500"
                onclick={startUpdate}
              >
                {$t("Download and Install")}
              </button>
            </footer>
          {:else}
            <div class="flex items-center justify-center">
              <Progress
                value={Math.round(downloadProgress)}
                max={100}
                class="relative mb-4 flex w-fit justify-center"
              >
                <div class="absolute inset-0 flex items-center justify-center">
                  <Progress.ValueText />
                </div>
                <Progress.Circle>
                  <Progress.CircleTrack />
                  <Progress.CircleRange />
                </Progress.Circle>
              </Progress>
            </div>
          {/if}
        </Dialog.Content>
      </Dialog.Positioner>
    </Portal>
  </Dialog>
{/if}
