<script lang="ts">
  import { profiles, settings } from "$lib/stores.svelte";
  import { invoke } from "@tauri-apps/api/core";
  import { applySettings } from "$lib/utils/settings";
  import type { AppSettings } from "$pytauri/_apiTypes";
  import ProfileList from "./ProfileList.svelte";
  import ProfileControls from "./ProfileControls.svelte";
  import ProfileState from "./ProfileState.svelte";

  interface Props {
    collapsed: boolean;
    onAddProfile: () => void;
    onDeleteProfile?: (index: number) => void;
    onRenameProfile?: (index: number, newName: string) => void;
  }

  let { collapsed, onAddProfile, onDeleteProfile, onRenameProfile }: Props =
    $props();

  const runningCount = $derived(
    profiles.states.filter((p) => p?.active_task).length,
  );

  async function selectProfile(index: number) {
    if (!settings.settings) return;
    profiles.select(index);

    try {
      const newSettings = {
        ...settings.settings,
        profiles: { ...settings.settings.profiles, active_profile: index },
      };
      const savedSettings: AppSettings = await invoke("save_app_settings", {
        settings: newSettings,
      });
      await applySettings(savedSettings);
    } catch (e) {
      console.error("Failed to save active profile:", e);
    }
  }
</script>

{#if !collapsed}
  <div class="sidebar">
    <ProfileControls {collapsed} {onAddProfile} />
    <ProfileList
      {collapsed}
      onSelectProfile={selectProfile}
      {onRenameProfile}
      {onDeleteProfile}
    />
    <ProfileState
      {collapsed}
      profilesLength={profiles.states.length}
      {runningCount}
    />
  </div>
{:else}
  <ProfileList
    {collapsed}
    onSelectProfile={selectProfile}
    {onRenameProfile}
    {onDeleteProfile}
  />
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
</style>
