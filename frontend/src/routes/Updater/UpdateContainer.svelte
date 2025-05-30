<script lang="ts">
  import {
    TerminateGameProcess,
    CheckForUpdates,
    DownloadUpdate,
  } from "$lib/wailsjs/go/main/App";
  import { updater } from "$lib/wailsjs/go/models";
  import { enablePolling, disablePolling } from "$lib/stores/polling";
  import { EventsOn } from "$lib/wailsjs/runtime/runtime";
  import { LogError, LogInfo } from "$lib/wailsjs/runtime";
  import { version } from "$app/environment";
  import { getItem, setItem } from "$lib/indexedDB";
  import UpdateIconSticky from "./UpdateIconSticky.svelte";
  import UpdateModal from "./UpdateModal.svelte";
  import { onDestroy } from "svelte";

  // Version utilities
  const versionUtils = {
    compare: (v1: string, v2: string): number => {
      const parts1 = v1.split(".").map(Number);
      const parts2 = v2.split(".").map(Number);
      for (let i = 0; i < Math.max(parts1.length, parts2.length); i++) {
        const part1 = parts1[i] || 0;
        const part2 = parts2[i] || 0;
        if (part1 < part2) return -1;
        if (part1 > part2) return 1;
      }
      return 0;
    },

    isInRange: (
      version: string,
      startVersion: string,
      endVersion: string,
    ): boolean => {
      return (
        versionUtils.compare(version, startVersion) > 0 &&
        versionUtils.compare(version, endVersion) <= 0
      );
    },
  };

  interface Release {
    html_url: string;
    tag_name: string;
    assets: Asset[];
    body: string;
  }

  interface Asset {
    name: string;
    browser_download_url: string;
  }

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
  let modalChangeLog: string = $state("");

  async function getModalChangeLog(
    currentVersion: string,
    latestVersion: string,
  ): Promise<string> {
    const releasesResponse = await fetch(
      "https://api.github.com/repos/AdbAutoPlayer/AdbAutoPlayer/releases",
    );
    const allReleases: Release[] = await releasesResponse.json();

    const filteredReleases = allReleases.filter((release) => {
      const releaseVersion = release.tag_name;
      return versionUtils.isInRange(
        releaseVersion,
        currentVersion,
        latestVersion,
      );
    });

    let changeLog: string = "";
    let changeLogs: Array<string> = [];
    filteredReleases.forEach((release: Release) => {
      let body = release.body.replace(/\*\*Full Changelog\*\*:.*/, "");
      body = body.trim();
      if (body !== "") {
        changeLogs.push(`# ${release.tag_name}\n${body}\n\n`);
      }
    });

    if (changeLogs.length > 0) {
      changeLog = changeLogs.join("\n___\n");
      changeLog +=
        "\n___\n**Full Changelog**: https://github.com/AdbAutoPlayer/AdbAutoPlayer/compare/" +
        `${currentVersion}...${latestVersion}`;
    }

    return changeLog;
  }

  async function initialUpdateCheck() {
    LogInfo(`App Version: ${version}`);
    let lastAppVersion = await getItem<string>("lastAppVersion");
    if (!lastAppVersion) {
      lastAppVersion = version;
      await setItem("lastAppVersion", version);
    }

    try {
      const info = await CheckForUpdates();
      console.log(info);
      if (info.error) {
        LogError(info.error);
      }
      if (info.available) {
        updateState.isInitialUpdateCheck = true;
        await setAvailableUpdateInfo(info);
        updateState.autoUpdate = info.autoUpdate;
        await openModal();
      }
    } catch (error) {
      console.error(error);
      LogError(`Update check failed: ${error}`);
      enablePolling();
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
      LogError(`Update failed: ${error}`);
      updateState.isDownloading = false;
      alert(`Update failed: ${error}`);
      closeModal();
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
    modalChangeLog = await getModalChangeLog(version, updateInfo.version);
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
      console.error(error);
      LogError(`Update check failed: ${error}`);
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
  {modalChangeLog}
  downloadProgress={updateState.downloadProgress}
  isDownloading={updateState.isDownloading}
  onClose={closeModal}
  onStartUpdate={startUpdate}
/>
