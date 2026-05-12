<script lang="ts">
  import { t } from "$lib/i18n/i18n";
  import { activeProfile, profileStates, appSettings } from "$lib/stores";
  import { invoke } from "@tauri-apps/api/core";
  import { applySettings } from "$lib/utils/settings";
  import type { AppSettings } from "$pytauri/_apiTypes";

  interface Props {
    collapsed: boolean;
    onAddProfile: () => void;
    onDeleteProfile?: (index: number) => void;
    onRenameProfile?: (index: number, newName: string) => void;
  }

  let { collapsed, onAddProfile, onDeleteProfile, onRenameProfile }: Props =
    $props();

  const profiles = $derived($appSettings?.profiles?.profiles ?? []);
  const runningCount = $derived(
    $profileStates.filter((p) => p?.active_task).length,
  );

  async function selectProfile(index: number) {
    if (!$appSettings) return;
    $activeProfile = index;

    try {
      const newSettings = {
        ...$appSettings,
        profiles: { ...$appSettings.profiles, active_profile: index },
      };
      const savedSettings: AppSettings = await invoke("save_app_settings", {
        settings: newSettings,
      });
      await applySettings(savedSettings);
    } catch (e) {
      console.error("Failed to save active profile:", e);
    }
  }

  function getStatus(index: number) {
    const p = $profileStates[index];
    if (!p?.device_id) return "offline";
    if (p.active_task) return "running";
    return "idle";
  }

  const dotColors = {
    running: "var(--ok)",
    idle: "var(--warn)",
    offline: "var(--text-4)",
  };
</script>

{#if !collapsed}
  <div class="sidebar">
    <div class="header">
      <div class="title">{$t("Profiles")}</div>
      <button
        class="icon-btn-small"
        title={$t("Add profile")}
        onclick={onAddProfile}
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          width="14"
          height="14"><path d="M12 5v14M5 12h14" /></svg
        >
      </button>
    </div>

    <div class="list">
      {#each profiles as p, i}
        {@const status = getStatus(i)}
        {@const selected = i === $activeProfile}
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
          class="profile-row"
          class:selected
          onclick={() => selectProfile(i)}
        >
          <div class="icon-container">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.7"
              stroke-linecap="round"
              stroke-linejoin="round"
              width="14"
              height="14"
              ><rect x="6" y="2" width="12" height="20" rx="2" /><path
                d="M11 18h2"
              /></svg
            >
            <span class="status-dot" style="background: {dotColors[status]}"
            ></span>
          </div>
          <div class="info">
            <div class="name-row">
              <div class="name">{p}</div>
            </div>
            <div class="device">
              {$profileStates[i]?.device_id || $t("no device")}
            </div>
            <div class="task" class:running={status === "running"}>
              {#if $profileStates[i]?.active_task}
                {@const activeT = $profileStates[i].active_task}
                {@const opt = $profileStates[i].game_menu?.menu_options?.find(
                  (o) => o.label === activeT,
                )}
                <span class="play-icon">▸</span>
                {opt?.custom_label ?? opt?.label ?? activeT}
              {:else if $profileStates[i]?.game_menu?.game_title}
                {$t($profileStates[i]?.game_menu?.game_title)} · {$t("Idle")}
              {:else}
                {$t("No game")}
              {/if}
            </div>
          </div>
          <div class="row-actions">
            <button
              class="action-btn-mini"
              title={$t("Rename profile")}
              onclick={(e) => {
                e.stopPropagation();
                const newName = prompt($t("Enter new profile name:"), p);
                if (newName && newName.trim() && newName.trim() !== p) {
                  onRenameProfile?.(i, newName.trim());
                }
              }}
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                width="12"
                height="12"
                ><path
                  d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"
                /></svg
              >
            </button>
            {#if profiles.length > 1}
              <button
                class="action-btn-mini delete"
                title={$t("Delete profile")}
                onclick={(e) => {
                  e.stopPropagation();
                  onDeleteProfile?.(i);
                }}
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  width="12"
                  height="12"><path d="M18 6 6 18M6 6l12 12" /></svg
                >
              </button>
            {/if}
          </div>
        </div>
      {/each}
    </div>

    <div class="footer">
      <span>{profiles.length} {$t("profiles")}</span>
      <span class="mono">{runningCount} {$t("running")}</span>
    </div>
  </div>
{:else}
  <div class="rail">
    {#each profiles as p, i}
      {@const status = getStatus(i)}
      {@const selected = i === $activeProfile}
      <button
        class="rail-btn"
        class:selected
        onclick={() => selectProfile(i)}
        title={`${p} — ${$profileStates[i]?.device_id || $t("offline")}`}
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.7"
          stroke-linecap="round"
          stroke-linejoin="round"
          width="14"
          height="14"
          ><rect x="6" y="2" width="12" height="20" rx="2" /><path
            d="M11 18h2"
          /></svg
        >
        <span class="status-dot-mini" style="background: {dotColors[status]}"
        ></span>
      </button>
    {/each}
  </div>
{/if}

<style>
  .sidebar {
    width: 248px;
    flex: 0 0 248px;
    display: flex;
    flex-direction: column;
    border-right: 1px solid var(--line);
    background: var(--bg-1);
    min-width: 0;
  }

  .header {
    padding: 14px 14px 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .title {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-3);
  }

  .icon-btn-small {
    width: 24px;
    height: 24px;
    border-radius: 8px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--text-2);
    transition:
      background var(--dur-1),
      color var(--dur-1);
  }

  .icon-btn-small:hover {
    background: var(--bg-hover);
    color: var(--text-1);
  }

  .list {
    padding: 4px 8px;
    flex: 1;
    overflow: auto;
  }

  .profile-row {
    width: 100%;
    text-align: left;
    display: flex;
    gap: 10px;
    align-items: center;
    padding: 9px 10px;
    border-radius: 8px;
    margin-bottom: 2px;
    background: transparent;
    color: var(--text-2);
    border: 1px solid transparent;
    transition:
      background var(--dur-1),
      border-color var(--dur-1);
  }

  .profile-row:hover {
    background: var(--bg-2);
  }

  .profile-row.selected {
    background: var(--accent-ghost);
    color: var(--text-1);
    border: 1px solid color-mix(in oklab, var(--accent) 30%, transparent);
  }

  .icon-container {
    position: relative;
    width: 28px;
    height: 28px;
    border-radius: 7px;
    background: var(--bg-3);
    display: grid;
    place-items: center;
    color: var(--text-3);
    flex: 0 0 28px;
  }

  .status-dot {
    position: absolute;
    bottom: -2px;
    right: -2px;
    width: 10px;
    height: 10px;
    border-radius: 999px;
    border: 2px solid var(--bg-1);
  }

  .info {
    min-width: 0;
    flex: 1;
  }

  .name {
    font-weight: 600;
    font-size: 13px;
    letter-spacing: -0.005em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .device {
    font-size: 11px;
    color: var(--text-3);
    font-family: var(--font-mono);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .task {
    font-size: 11px;
    color: var(--text-3);
    margin-top: 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .task.running {
    color: var(--text-2);
  }

  .play-icon {
    color: var(--ok);
  }

  .footer {
    padding: 10px 12px;
    border-top: 1px solid var(--line);
    font-size: 11px;
    color: var(--text-4);
    display: flex;
    justify-content: space-between;
  }

  .mono {
    font-family: var(--font-mono);
  }

  .rail {
    width: 52px;
    flex: 0 0 52px;
    border-right: 1px solid var(--line);
    background: var(--bg-1);
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 10px 0;
    gap: 4px;
  }

  .rail-btn {
    position: relative;
    width: 36px;
    height: 36px;
    border-radius: 9px;
    display: grid;
    place-items: center;
    background: var(--bg-2);
    color: var(--text-3);
    border: 1px solid var(--line);
  }

  .rail-btn.selected {
    background: var(--accent-ghost);
    color: var(--accent);
    border: 1px solid color-mix(in oklab, var(--accent) 40%, transparent);
  }

  .status-dot-mini {
    position: absolute;
    bottom: -2px;
    right: -2px;
    width: 10px;
    height: 10px;
    border-radius: 999px;
    border: 2px solid var(--bg-1);
  }
  .row-actions {
    display: flex;
    gap: 2px;
    opacity: 0;
    transition: opacity var(--dur-1);
  }

  .profile-row:hover .row-actions {
    opacity: 1;
  }

  .action-btn-mini {
    width: 24px;
    height: 24px;
    border-radius: 6px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--text-4);
    background: transparent;
    border: none;
    cursor: pointer;
    transition:
      background var(--dur-1),
      color var(--dur-1);
  }

  .action-btn-mini:hover {
    background: var(--bg-hover);
    color: var(--text-1);
  }

  .action-btn-mini.delete:hover {
    color: var(--warn);
  }
</style>
