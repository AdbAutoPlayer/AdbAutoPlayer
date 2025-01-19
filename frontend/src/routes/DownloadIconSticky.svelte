<script lang="ts">
  import { version } from "$app/environment";
  import { UpdatePatch } from "$lib/wailsjs/go/main/App";
  import { logoAwake } from "$lib/stores/logo";
  import { LogError, LogInfo } from "$lib/wailsjs/runtime";
  import { marked } from "marked";
  import Modal from "./Modal.svelte";
  let downloadIconImageSrc: string | null = $state(null);
  let releaseHtmlDownloadUrl: string = $state(
    "https://github.com/yulesxoxo/AdbAutoPlayer/releases",
  );
  let showModal = $state(false);
  let modalRelease: Release | undefined = $state();
  let modalAsset: Asset | undefined = $state();
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

  function getFilenamesBasedOnPlatform() {
    let appFileName = "AdbAutoPlayer_Windows.zip";
    let patchFileName = "Patch_Windows.zip";

    let userAgent = navigator.userAgent.toLowerCase();

    appFileName = "AdbAutoPlayer_Windows.zip";
    patchFileName = "Patch_Windows.zip";
    if (userAgent.includes("mac")) {
      appFileName = "AdbAutoPlayer_Linux.zip";
      patchFileName = "Patch_Linux.zip";
    }

    return { appFileName: appFileName, patchFileName: patchFileName };
  }

  async function checkForNewRelease(currentVersion: string): Promise<void> {
    currentVersion = currentVersion.startsWith("v")
      ? currentVersion.slice(1)
      : currentVersion;
    try {
      const response = await fetch(
        "https://api.github.com/repos/yulesxoxo/AdbAutoPlayer/releases/latest",
      );
      const releaseData: Release = await response.json();

      const { appFileName, patchFileName } = getFilenamesBasedOnPlatform();
      modalAsset = releaseData.assets.find(
        (a: Asset) => a.name === appFileName,
      );

      if (!modalAsset) {
        console.log("Release still building");
        return;
      }

      if (response.ok && releaseData.tag_name) {
        const latestVersion = releaseData.tag_name.startsWith("v")
          ? releaseData.tag_name.slice(1)
          : releaseData.tag_name;

        const currentParts = currentVersion.split(".").map(Number);
        const latestParts = latestVersion.split(".").map(Number);
        if (
          latestParts[0] > currentParts[0] ||
          (latestParts[0] == currentParts[0] &&
            latestParts[1] > currentParts[1])
        ) {
          modalRelease = releaseData;
          notifyUpdate(modalAsset);
          return;
        }

        if (
          latestParts[0] === currentParts[0] &&
          latestParts[1] === currentParts[1] &&
          latestParts[2] > currentParts[2]
        ) {
          const patch = releaseData.assets.find(
            (a: Asset) => a.name === patchFileName,
          );
          if (!patch) {
            console.log("No asset found");
            return;
          }

          $logoAwake = false;
          UpdatePatch(patch.browser_download_url)
            .then(() => {
              localStorage.setItem("downloadedVersion", releaseData.tag_name);
              LogInfo("Version: " + releaseData.tag_name);
              $logoAwake = true;
            })
            .catch((err) => {
              alert(err);
              $logoAwake = true;
            });
        }

        console.log("No new version available");
      } else {
        LogError("Failed to fetch release data");
      }
    } catch (error) {
      LogError("Error checking for new release:" + error);
    }
  }

  function notifyUpdate(asset: Asset) {
    downloadIconImageSrc = "/icons/download-cloud.svg";
    releaseHtmlDownloadUrl = asset.browser_download_url;
    showModal = true;
  }

  function isVersionGreater(v1: string, v2: string) {
    const [major1, minor1, patch1] = v1.split(".").map(Number);
    const [major2, minor2, patch2] = v2.split(".").map(Number);

    if (major1 !== major2) return major1 > major2;
    if (minor1 !== minor2) return minor1 > minor2;
    return patch1 > patch2;
  }

  function runVersionUpdate() {
    let currentVersion = localStorage.getItem("downloadedVersion");
    if (!currentVersion || isVersionGreater(version, currentVersion)) {
      currentVersion = version;
    }
    if (version === "0.0.0") {
      LogInfo("Version: dev");
      LogInfo("Skipping update for dev");
      return;
    }
    LogInfo("Version: " + currentVersion);
    checkForNewRelease(currentVersion);
  }

  function downloadAsset() {
    if (modalAsset) {
      const a = document.createElement("a");
      a.href = modalAsset.browser_download_url;
      a.download = "";
      a.click();
      downloadIconImageSrc = null;
    }
  }

  runVersionUpdate();
</script>

{#if downloadIconImageSrc}
  <a href={releaseHtmlDownloadUrl} class="download-icon-sticky">
    <img
      src={downloadIconImageSrc}
      alt="Download"
      width="24"
      height="24"
      draggable="false"
    />
  </a>
{/if}

<Modal bind:showModal>
  {#snippet header()}
    <h2>
      Update Available: {modalRelease?.tag_name}
    </h2>
  {/snippet}
  {@html marked(modalRelease?.body || "")}
  {#snippet footer()}
    {#if modalAsset}
      <button style="display: inline-block" onclick={downloadAsset}
        >Download</button
      >
    {/if}
  {/snippet}
</Modal>

<style>
  .download-icon-sticky {
    user-select: none;
    position: fixed;
    top: 10px;
    right: 10px;
    z-index: 1000;
    cursor: pointer;
    background: transparent;
    border: none;
    padding: 0;
    outline: none;
    box-shadow: none;
  }

  .download-icon-sticky img {
    display: block;
  }
</style>
