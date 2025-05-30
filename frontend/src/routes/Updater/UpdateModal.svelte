<script lang="ts">
  import marked from "$lib/markdownRenderer";
  import { updater } from "$lib/wailsjs/go/models";
  import Modal from "../Components/Modal.svelte";
  import { ProgressRing } from "@skeletonlabs/skeleton-svelte";

  interface Props {
    showModal: boolean;
    updateInfo: updater.UpdateInfo | null;
    modalChangeLog: string;
    downloadProgress: number;
    isDownloading: boolean;
    onClose: () => void;
    onStartUpdate: () => void;
  }

  let {
    showModal = $bindable(),
    updateInfo,
    modalChangeLog,
    downloadProgress,
    isDownloading,
    onClose,
    onStartUpdate,
  }: Props = $props();
</script>

<Modal bind:showModal {onClose}>
  {#snippet modalContent()}
    <div class="flex h-full flex-col">
      <h2 class="mb-4 text-center h2 text-2xl">
        {#if isDownloading}
          Downloading Update... {Math.round(downloadProgress)}%
        {:else}
          Update Available: {updateInfo?.version || ""}
        {/if}
      </h2>

      {#if isDownloading}
        <!-- Progress Ring -->
        <div class="mb-4">
          <div class="mb-4 flex justify-center">
            <ProgressRing
              value={Math.round(downloadProgress)}
              max={100}
              showLabel
            />
          </div>
        </div>

        {#if downloadProgress >= 100}
          <!-- Update Complete Message -->
          <div class="py-8 text-center">
            <p class="text-lg text-success-500">
              Update downloaded successfully! The application will restart
              automatically.
            </p>
          </div>
        {/if}
      {:else}
        <!-- Changelog Content -->
        <div
          class="min-h-0 flex-grow overflow-y-auto pr-2 break-words whitespace-normal"
        >
          {@html marked(modalChangeLog || "")}
        </div>
      {/if}

      {#if !isDownloading}
        <!-- Action Buttons -->
        <div
          class="border-surface-200-700 mt-4 flex justify-end gap-2 border-t pt-4"
        >
          {#if updateInfo}
            <button
              class="btn preset-filled-primary-100-900 hover:preset-filled-primary-500"
              onclick={onStartUpdate}
            >
              Update Now
            </button>
          {/if}

          <button
            class="btn preset-filled-surface-100-900 hover:preset-filled-surface-500"
            onclick={onClose}
          >
            Later
          </button>
        </div>
      {/if}
    </div>
  {/snippet}
</Modal>
