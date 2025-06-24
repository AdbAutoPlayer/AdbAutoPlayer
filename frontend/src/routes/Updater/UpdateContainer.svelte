<script lang="ts">
  import {
    TerminateGameProcess,
    CheckForUpdates,
    DownloadUpdate,
    GetChangelogs,
  } from "$lib/wailsjs/go/main/App";
  import { updater } from "$lib/wailsjs/go/models";
  import { enablePolling, disablePolling } from "$lib/stores/polling";
  import { EventsOn } from "$lib/wailsjs/runtime/runtime";
  import { LogInfo } from "$lib/wailsjs/runtime";
  import { version } from "$app/environment";
  import UpdateIconSticky from "./UpdateIconSticky.svelte";
  import UpdateModal from "./UpdateModal.svelte";
  import { onDestroy } from "svelte";
  import { showErrorToast } from "$lib/utils/error";

  // State management
  let updateState = $state({
    showDownloadIcon: false,
    showModal: false,
    downloadProgress: 0,
    isDownloading: false,
    autoUpdate: false,
    isInitialUpdateCheck: false,
  });

  let updateInfo: updater.UpdateInfo | null = $state(null);
  let modalChangelogs: updater.Changelog[] = $state([]);

  async function initialUpdateCheck() {
    LogInfo(`App Version: ${version}`);

    try {
      const info = await CheckForUpdates();
      console.log(info);
      if (info.available) {
        updateState.isInitialUpdateCheck = true;
        await setAvailableUpdateInfo(info);
        updateState.autoUpdate = info.autoUpdate;
        await openModal();
      }
    } catch (error) {
      showErrorToast(error, { title: "Failed to Check for Updates" });
    }

    if (!updateState.isInitialUpdateCheck) {
      enablePolling();
    }
  }

  async function startUpdate() {
    if (!updateInfo) return;

    disablePolling();
    await TerminateGameProcess();

    updateState.isDownloading = true;
    updateState.downloadProgress = 0;

    try {
      const unsubscribe = EventsOn("download-progress", (progress: number) => {
        updateState.downloadProgress = progress;
      });

      await DownloadUpdate(updateInfo.downloadURL);
      unsubscribe();
    } catch (error) {
      showErrorToast(error, { title: "Failed to Update" });
    }
  }

  function closeModal() {
    if (updateState.isDownloading) {
      updateState.showModal = true;
      return;
    }

    if (updateState.isInitialUpdateCheck) {
      enablePolling();
      updateState.isInitialUpdateCheck = false;
    }
    updateState.showModal = false;
  }

  async function openModal() {
    updateState.showModal = true;
    if (updateState.autoUpdate) {
      await startUpdate();
    }
  }

  async function setAvailableUpdateInfo(info: updater.UpdateInfo) {
    updateInfo = info;
    modalChangelogs = await GetChangelogs();
    updateState.showDownloadIcon = true;
  }

  async function checkForUpdates() {
    updateState.autoUpdate = false; // At this point we do not want to auto update it would interrupt whatever action is running without the user knowing about it.

    try {
      const info = await CheckForUpdates();
      if (info.available) {
        await setAvailableUpdateInfo(info);
      }
    } catch (error) {
      showErrorToast(error, { title: "Failed to Check for Updates" });
    }
  }

  // Initialize version check
  initialUpdateCheck();

  // Periodic update check
  const UPDATE_CHECK_INTERVAL = 15 * 60 * 1000; // Check every 15 minutes (in milliseconds)
  const updateCheckInterval = setInterval(
    checkForUpdates,
    UPDATE_CHECK_INTERVAL,
  );

  // Clean up interval when component is destroyed
  onDestroy(() => {
    clearInterval(updateCheckInterval);
  });
</script>

<UpdateIconSticky show={updateState.showDownloadIcon} onClick={openModal} />

<UpdateModal
  bind:showModal={updateState.showModal}
  {updateInfo}
  {modalChangelogs}
  downloadProgress={updateState.downloadProgress}
  isDownloading={updateState.isDownloading}
  onClose={closeModal}
  onStartUpdate={startUpdate}
/>
