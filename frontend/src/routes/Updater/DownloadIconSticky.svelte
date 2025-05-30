<script lang="ts">
  import { TerminateGameProcess } from "$lib/wailsjs/go/main/App";
  import marked from "$lib/markdownRenderer";
  import { version } from "$app/environment";
  import { CheckForUpdates, DownloadUpdate } from "$lib/wailsjs/go/main/App";
  import { updater } from "\$lib/wailsjs/go/models";
  import { pollRunningGame, pollRunningProcess } from "$lib/stores/polling";
  import { EventsOn } from "\$lib/wailsjs/runtime/runtime";
  import { LogError, LogInfo } from "$lib/wailsjs/runtime";
  import DownloadModal from "./DownloadModal.svelte";
  import { getItem, setItem } from "$lib/indexedDB";
  import { ProgressRing } from "@skeletonlabs/skeleton-svelte";

  // State management
  let showDownloadIcon: boolean = $state(false);
  let showModal = $state(false);
  let downloadProgress: number = $state(0);
  let isDownloading: boolean = $state(false);
  let autoUpdate: boolean = $state(false);
  let isRunVersionUpdate: boolean = $state(false);

  // Update info
  let updateInfo: updater.UpdateInfo | null = $state(null);
  let modalChangeLog: string = $state("");

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

  function isVersionInRange(
    version: string,
    startVersion: string,
    endVersion: string,
  ): boolean {
    const compareVersions = (v1: string, v2: string) => {
      const parts1 = v1.split(".").map(Number);
      const parts2 = v2.split(".").map(Number);
      for (let i = 0; i < Math.max(parts1.length, parts2.length); i++) {
        const part1 = parts1[i] || 0;
        const part2 = parts2[i] || 0;
        if (part1 < part2) return -1;
        if (part1 > part2) return 1;
      }
      return 0;
    };

    return (
      compareVersions(version, startVersion) > 0 &&
      compareVersions(version, endVersion) <= 0
    );
  }

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
      return isVersionInRange(releaseVersion, currentVersion, latestVersion);
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

  async function runVersionUpdate() {
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
        isRunVersionUpdate = true;
        await setAvailableUpdateInfo(info);
        autoUpdate = info.autoUpdate;
        await openModal();
      }
    } catch (error) {
      console.error(error);
      LogError(`Update check failed: ${error}`);
      $pollRunningGame = true;
      $pollRunningProcess = true;
    }

    if (!isRunVersionUpdate) {
      $pollRunningGame = true;
      $pollRunningProcess = true;
    }
  }

  async function startUpdate() {
    if (!updateInfo) return;

    $pollRunningGame = false;
    $pollRunningProcess = false;
    await TerminateGameProcess();

    isDownloading = true;
    downloadProgress = 0;

    try {
      // Listen for download progress events
      const unsubscribe = EventsOn("download-progress", (progress: number) => {
        downloadProgress = progress;
      });

      await DownloadUpdate(updateInfo.downloadURL);
      unsubscribe();
    } catch (error) {
      console.error("Update failed:", error);
      LogError(`Update failed: ${error}`);
      isDownloading = false;
      alert(`Update failed: ${error}`);
    }
  }

  function closeModal() {
    if (isDownloading) {
      showModal = true;
      return;
    }

    if (isRunVersionUpdate) {
      $pollRunningGame = true;
      $pollRunningProcess = true;
      isRunVersionUpdate = false;
    }
    showModal = false;
  }

  async function openModal() {
    showModal = true;
    if (autoUpdate) {
      await startUpdate();
    }
  }

  // Initialize version check
  runVersionUpdate();

  async function setAvailableUpdateInfo(info: updater.UpdateInfo) {
    updateInfo = info;
    modalChangeLog = await getModalChangeLog(version, updateInfo.version);
    showDownloadIcon = true;
  }

  async function checkForUpdates() {
    autoUpdate = false; // At this point we do not want to auto update it would interrupt whatever action is running without the user knowing about it.

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

  const UPDATE_CHECK_INTERVAL = 15 * 60 * 1000; // Check every 15 minutes (in milliseconds)
  setTimeout(checkForUpdates, UPDATE_CHECK_INTERVAL);
</script>

<!-- Download Icon - shown when update is available but modal is closed -->
{#if showDownloadIcon}
  <button
    onclick={openModal}
    class="fixed top-0 right-0 z-50 m-2 cursor-pointer rounded-full bg-primary-500 p-2 shadow-lg transition-colors select-none hover:bg-primary-600"
    draggable="false"
    title="Update Available"
  >
    <img
      src="/icons/download-cloud.svg"
      alt="Download"
      width="24"
      height="24"
      draggable="false"
    />
  </button>
{/if}

<DownloadModal bind:showModal onClose={closeModal}>
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
              onclick={startUpdate}
            >
              Update Now
            </button>
          {/if}

          <button
            class="btn preset-filled-surface-100-900 hover:preset-filled-surface-500"
            onclick={closeModal}
          >
            Later
          </button>
        </div>
      {/if}
    </div>
  {/snippet}
</DownloadModal>
