<script lang="ts">
  import { pollRunningGame } from "$lib/stores/polling";
  import { version } from "$app/environment";
  import UpdateIconSticky from "$lib/components/sticky/UpdateIconSticky.svelte";
  import UpdateModal from "./UpdateModal.svelte";
  import { onDestroy } from "svelte";
  import { showErrorToast } from "$lib/toast/toast-error";
  import { logInfo } from "$lib/log/log-events";
  import { Events } from "@wailsio/runtime";
  import { EventNames } from "$lib/log/eventNames";
  import {
    CheckForUpdates,
    DownloadUpdate,
    GetChangelogs,
  } from "@wails/updater/updateservice";
  import { UpdateInfo, Changelog } from "@wails/updater";

  // State management
  let updateState = $state({
    showDownloadIcon: false,
    showModal: false,
    downloadProgress: 0,
    isDownloading: false,
    autoUpdate: false,
    isInitialUpdateCheck: false,
    disabled: false,
    redirectToGitHub: false,
  });

  let updateInfo: UpdateInfo | null = $state(null);
  let modalChangelogs: Changelog[] = $state([]);

  async function initialUpdateCheck() {
    logInfo(`App Version: ${version}`);

    try {
      const info = await CheckForUpdates();
      if (info.disabled) {
        updateState.disabled = true;
        clearInterval(updateCheckInterval);
      } else if (info.available) {
        updateState.isInitialUpdateCheck = true;
        await setAvailableUpdateInfo(info);
        updateState.autoUpdate = info.autoUpdate;
        await openModal();
      }
    } catch (error) {
      showErrorToast(error, { title: "Failed to Check for Updates" });
    }

    if (!updateState.isInitialUpdateCheck) {
      $pollRunningGame = true;
    }
  }

  async function startUpdate() {
    if (!updateInfo) return;

    $pollRunningGame = false;

    Events.OffAll();
    updateState.isDownloading = true;
    updateState.downloadProgress = 0;

    try {
      const unsubscribe = Events.On(EventNames.DOWNLOAD_PROGRESS, (ev) => {
        updateState.downloadProgress = ev.data;
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
      $pollRunningGame = true;
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

  async function setAvailableUpdateInfo(info: UpdateInfo) {
    updateInfo = info;
    modalChangelogs = await GetChangelogs();
    updateState.showDownloadIcon = true;
  }

  async function checkForUpdates() {
    if (updateState.disabled) {
      // Should not happen because the update check interval is already cleared but doesn't hurt.
      return;
    }
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
