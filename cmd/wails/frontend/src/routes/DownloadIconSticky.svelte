<script lang="ts">
    import { version } from '$app/environment';
    import {
        UpdatePatch
    } from "$lib/wailsjs/go/main/App";
    import {LogError, LogInfo} from "$lib/wailsjs/runtime";
    let downloadIconImageSrc: string|null = $state(null)

    async function checkForNewRelease(currentVersion: string): Promise<void> {
        currentVersion= currentVersion.startsWith('v')
            ? currentVersion.slice(1)
            : currentVersion;
        try {
            const response = await fetch('https://api.github.com/repos/yulesxoxo/AdbAutoPlayer/releases/latest');
            const releaseData = await response.json();

            if (response.ok && releaseData.tag_name) {
                const latestVersion = releaseData.tag_name.startsWith('v')
                    ? releaseData.tag_name.slice(1)
                    : releaseData.tag_name

                const currentParts = currentVersion.split('.').map(Number);
                const latestParts = latestVersion.split('.').map(Number);
                console.log(currentParts)
                console.log(latestParts)
                if (
                    latestParts[0] > currentParts[0]
                    || latestParts[1] > currentParts[1]
                ) {
                    notifyUpdate()
                    return;
                }
                if (
                    latestParts[0] === currentParts[0]
                    && latestParts[1] === currentParts[1]
                    && latestParts[2] > currentParts[2]
                ) {
                    const asset = releaseData.assets.find((a: any) => a.name === 'patch.zip');
                    if (!asset) {
                        console.log("No asset found")
                        return;
                    }

                    const downloadUrl = asset.browser_download_url
                    if (!downloadUrl) {
                        console.log("No browser_download_url found")
                        return;
                    }
                    UpdatePatch(downloadUrl)
                        .then(() => {
                            localStorage.setItem("downloadedVersion", releaseData.latestVersion);
                        })
                        .catch((err) => {
                            alert(err)
                        })
                    ;
                }

                console.log("No new version available")
            } else {
                LogError('Failed to fetch release data');
            }
        } catch (error) {
            LogError('Error checking for new release:' + error);
        }
    }

    function notifyUpdate() {
        downloadIconImageSrc = "/icons/download-cloud.svg"
        alert("New update available click the download button on the top right.")
    }

    let currentVersion = localStorage.getItem("downloadedVersion");
    if (!currentVersion) {
        currentVersion = version;
    }

    LogInfo("Version: " + currentVersion)
    if (currentVersion !== null && currentVersion !== undefined) {
        if(currentVersion === "0.0.0") {
            LogInfo("Skipping update for dev");
        } else {
            checkForNewRelease(currentVersion);
        }
    }

</script>

{#if downloadIconImageSrc}
    <a href="https://github.com/yulesxoxo/AdbAutoPlayer/releases" target="_blank" class="download-icon-sticky">
        <img src={downloadIconImageSrc}
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
