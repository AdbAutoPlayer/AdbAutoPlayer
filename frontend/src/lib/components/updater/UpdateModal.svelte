<script lang="ts">
  import marked from "$lib/utils/markdownRenderer";
  import { Progress } from "@skeletonlabs/skeleton-svelte";
  import { Changelog, UpdateInfo } from "@wails/updater";
  import { Dialog, Portal } from "@skeletonlabs/skeleton-svelte";

  function handleOpenChange(e: { open: boolean }) {
    if (e.open) {
      showModal = true;

      return;
    }

    if (onClose) {
      onClose();
      return;
    }

    showModal = false;
  }

  interface Props {
    showModal: boolean;
    updateInfo: UpdateInfo | null;
    modalChangelogs: Changelog[];
    downloadProgress: number;
    isDownloading: boolean;
    onClose: () => void;
    onStartUpdate: () => void;
  }

  let {
    showModal = $bindable(),
    updateInfo,
    modalChangelogs,
    downloadProgress,
    isDownloading,
    onClose,
    onStartUpdate,
  }: Props = $props();
</script>

<Dialog open={showModal} onOpenChange={handleOpenChange}>
  <Portal>
    <Dialog.Backdrop class="fixed inset-0 z-50 bg-surface-50-950/50" />
    <Dialog.Positioner
      class="fixed inset-0 z-50 flex items-center justify-center"
    >
      <Dialog.Content
        class="m-4 flex max-h-[90vh] max-w-screen-sm min-w-[280px] flex-col space-y-4 card bg-surface-100-900 p-5 shadow-xl"
      >
        <Dialog.Title>
          <h2 class="mb-4 text-center h2 text-2xl">
            {#if isDownloading}
              Downloading Update...
            {:else}
              Update Available: {updateInfo?.version || ""}
            {/if}
          </h2>
        </Dialog.Title>
        <Dialog.Description class="min-h-0 flex-1 overflow-y-auto">
          {#if isDownloading}
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
            <div class="py-8 text-center">
              <p class="text-lg">The App will restart automatically.</p>
            </div>
          {:else}
            <!-- Changelog Content -->
            <div
              class="min-h-0 flex-grow overflow-y-auto pr-2 break-words whitespace-normal"
            >
              {#each modalChangelogs as changelog}
                <div>
                  <div class="my-2 text-lg font-bold">
                    Changelog: {changelog.version}
                  </div>
                  {@html marked(changelog.body || "")}
                </div>
                <hr class="hr border-t-4" />
              {/each}
            </div>
          {/if}
        </Dialog.Description>
        {#if !isDownloading}
          <!-- Action Buttons -->
          <div
            class="border-surface-200-700 mt-4 flex justify-end gap-2 border-t pt-4"
          >
            {#if updateInfo}
              {#if updateInfo.redirectToGitHub}
                <a
                  class="btn preset-filled-primary-100-900 hover:preset-filled-primary-500"
                  href={updateInfo.releaseURL}
                  target="_blank"
                  draggable="false"
                >
                  Download on GitHub
                </a>
              {:else}
                <button
                  class="btn preset-filled-primary-100-900 hover:preset-filled-primary-500"
                  onclick={onStartUpdate}
                >
                  Update Now
                </button>
              {/if}
            {/if}

            <button
              class="btn preset-filled-surface-100-900 hover:preset-filled-surface-500"
              onclick={onClose}
            >
              Later
            </button>
          </div>
        {/if}
      </Dialog.Content>
    </Dialog.Positioner>
  </Portal>
</Dialog>
