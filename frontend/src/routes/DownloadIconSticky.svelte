<script lang="ts">
  import { version } from "$app/environment";
  import { UpdatePatch } from "$lib/wailsjs/go/main/App";
  import { logoAwake } from "$lib/stores/logo";
  import { LogError, LogInfo } from "$lib/wailsjs/runtime";
  import { marked } from "marked";
  import Modal from "./Modal.svelte";
  import { getItem, setItem } from "$lib/indexedDB";

  const renderer = new marked.Renderer();

  renderer.link = function ({ href, title, text }) {
    const target = "_blank";
    const titleAttr = title ? ` title="${title}"` : "";
    return `<a href="${href}" target="${target}" rel="noopener noreferrer"${titleAttr}>${text}</a>`;
  };
  let downloadIconImageSrc: string | null = $state(null);
  let releaseHtmlDownloadUrl: string = $state(
    "https://github.com/yulesxoxo/AdbAutoPlayer/releases",
  );
  let showModal = $state(false);
  let modalRelease: Release | undefined = $state();
  let modalChangeLog: string | undefined = $state();
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
      appFileName = "AdbAutoPlayer_MacOS.zip";
      patchFileName = "Patch_MacOS.zip";
    }

    return { appFileName: appFileName, patchFileName: patchFileName };
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
      "https://api.github.com/repos/yulesxoxo/AdbAutoPlayer/releases",
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
      body.trim();
      if (body !== "") {
        changeLogs.push(`# ${release.tag_name}\n${body}\n\n`);
      }
      if (changeLogs.length > 0) {
        changeLog = changeLogs.join("\n___\n");
        changeLog +=
          "\n___\n**Full Changelog**: https://github.com/yulesxoxo/AdbAutoPlayer/compare/" +
          `${currentVersion}...${latestVersion}`;
      }
    });

    return changeLog;
  }

  async function checkForNewRelease(currentVersion: string): Promise<void> {
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
        console.log(`Release still building: ${appFileName}`);
        return;
      }

      if (response.ok && releaseData.tag_name) {
        const latestVersion = releaseData.tag_name;

        if (latestVersion === currentVersion) {
          LogInfo("No updates found");
          return;
        }

        modalChangeLog = await getModalChangeLog(currentVersion, latestVersion);

        const currentParts = currentVersion.split(".").map(Number);
        const latestParts = latestVersion.split(".").map(Number);
        if (latestParts[0] > currentParts[0]) {
          modalRelease = releaseData;
          notifyUpdate(modalAsset);
          return;
        }

        if (
          latestParts[1] > currentParts[1] ||
          (latestParts[1] == currentParts[1] &&
            latestParts[2] > currentParts[2])
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
            .then(async () => {
              await setItem("patch", releaseData.tag_name);
              LogInfo(`Downloaded Patch Version: ${releaseData.tag_name}`);
              $logoAwake = true;
              modalRelease = releaseData;
              modalAsset = undefined;
              showModal = true;
            })
            .catch((err) => {
              alert(err);
              $logoAwake = true;
            });
          return;
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

  async function runVersionUpdate() {
    if (version === "0.0.0") {
      LogInfo(`App Version: dev`);
      LogInfo("Skipping update for dev");
      return;
    }

    let patchVersion = await getItem<string>("patch");
    console.log("patchVersion", patchVersion);

    if (!patchVersion || isVersionGreater(version, patchVersion)) {
      console.log(
        `Version ${version} is greater than Patch Version ${patchVersion}`,
      );
      patchVersion = version;
      await setItem("patch", version);
    }

    LogInfo(`Patch Version: ${patchVersion} App Version: ${version}`);
    await checkForNewRelease(patchVersion);
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
    {#if modalAsset}
      <h2>
        Update Available: {modalRelease?.tag_name}
      </h2>
    {:else}
      <h2>
        Update Downloaded: {modalRelease?.tag_name}
      </h2>
    {/if}
  {/snippet}
  {@html marked(modalChangeLog || "", { renderer: renderer })}
  {#snippet footer()}
    {#if modalAsset}
      <button style="display: inline-block" onclick={downloadAsset}>
        Download
      </button>
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
