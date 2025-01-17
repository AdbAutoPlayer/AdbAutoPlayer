<script lang="ts">
  import { version } from "$app/environment";
  import { UpdatePatch } from "$lib/wailsjs/go/main/App";
  import { logoAwake } from "$lib/stores/logo";
  import { LogError, LogInfo } from "$lib/wailsjs/runtime";
  let downloadIconImageSrc: string | null = $state(null);

  async function checkForNewRelease(currentVersion: string): Promise<void> {
    currentVersion = currentVersion.startsWith("v")
      ? currentVersion.slice(1)
      : currentVersion;
    try {
      const response = await fetch(
        "https://api.github.com/repos/yulesxoxo/AdbAutoPlayer/releases/latest",
      );
      const releaseData = await response.json();

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
          notifyUpdate();
          return;
        }
        if (
          latestParts[0] === currentParts[0] &&
          latestParts[1] === currentParts[1] &&
          latestParts[2] > currentParts[2]
        ) {
          const asset = releaseData.assets.find(
            (a: any) => a.name === "Patch_Windows.zip",
          );
          if (!asset) {
            console.log("No asset found");
            return;
          }

          const downloadUrl = asset.browser_download_url;
          if (!downloadUrl) {
            console.log("No browser_download_url found");
            return;
          }
          $logoAwake = false;
          UpdatePatch(downloadUrl)
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

  function notifyUpdate() {
    downloadIconImageSrc = "/icons/download-cloud.svg";
    alert("New update available click the download button on the top right.");
  }

  function isVersionGreater(v1: string, v2: string) {
    const [major1, minor1, patch1] = v1.split('.').map(Number);
    const [major2, minor2, patch2] = v2.split('.').map(Number);

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

  runVersionUpdate()
</script>

{#if downloadIconImageSrc}
  <a
    href="https://github.com/yulesxoxo/AdbAutoPlayer/releases"
    target="_blank"
    class="download-icon-sticky"
  >
    <img
      src={downloadIconImageSrc}
      alt="Download"
      width="24"
      height="24"
      draggable="false"
    />
  </a>
{/if}

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
