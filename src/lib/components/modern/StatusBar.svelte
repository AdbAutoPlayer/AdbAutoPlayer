<script lang="ts">
  import { t } from "$lib/i18n/i18n";
  import { profiles, settings } from "$lib/stores.svelte";

  interface Props {
    theme: "dark" | "light";
    onToggleTheme: () => void;
    onToggleSidebar: () => void;
    onToggleLog: () => void;
    onDocs: () => void;
    onAppSettings: () => void;
    onGameSettings: () => void;
    onAdbSettings: () => void;
    onDebug: () => void;
    onCustomizer: () => void;
    sidebarOpen: boolean;
    logOpen: boolean;
  }

  let {
    theme,
    onToggleTheme,
    onToggleSidebar,
    onToggleLog,
    onDocs,
    onAppSettings,
    onGameSettings,
    onAdbSettings,
    onDebug,
    onCustomizer,
    sidebarOpen,
    logOpen,
  }: Props = $props();

  const profile = $derived(profiles.states[profiles.active]);
  const status = $derived(
    profile?.device_id ? (profile.active_task ? "running" : "idle") : "offline",
  );

  const dotColor = $derived(
    {
      running: "var(--ok)",
      idle: "var(--warn)",
      offline: "var(--text-4)",
    }[status],
  );

  const statusText = $derived(
    {
      running: $t("Running"),
      idle: $t("Idle"),
      offline: $t("Offline"),
    }[status],
  );
</script>

<div class="status-bar">
  <button
    onclick={onToggleSidebar}
    title={$t("Toggle profiles")}
    class="icon-btn"
    class:active={sidebarOpen}
  >
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.7"
      stroke-linecap="round"
      stroke-linejoin="round"
      width="16"
      height="16"
      ><rect x="3" y="4" width="18" height="16" rx="2" /><path
        d="M9 4v16"
      /></svg
    >
  </button>

  <div class="brand">
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
      <defs>
        <linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="var(--accent-hi)" />
          <stop offset="1" stop-color="var(--accent-lo)" />
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="20" height="20" rx="6" fill="url(#lg)" />
      <path
        d="M8 16 L12 8 L16 16 M9.5 13 L14.5 13"
        stroke="white"
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
        fill="none"
      />
    </svg>
    <div class="brand-name">AdbAutoPlayer</div>
    <div class="version">v{settings.appVersion}</div>
  </div>

  <div class="divider"></div>

  <!-- current profile chip -->
  <div class="profile-chip">
    <span
      class="status-dot"
      style="background: {dotColor}; box-shadow: {status === 'running'
        ? `0 0 0 3px ${dotColor}22`
        : 'none'}; animation: {status === 'running'
        ? 'pulse 1.6s ease-in-out infinite'
        : 'none'}"
    ></span>
    <span class="profile-name"
      >{settings.settings?.profiles?.profiles?.[profiles.active] ??
        "Profile"}</span
    >
    <span class="sep">·</span>
    <span class="device-id">{profile?.device_id || $t("no device")}</span>
    <span class="sep-alt">·</span>
    <span class="status-label">{statusText}</span>
  </div>

  <div class="spacer"></div>

  <button class="icon-btn" title={$t("Customize Theme")} onclick={onCustomizer}>
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.7"
      stroke-linecap="round"
      stroke-linejoin="round"
      width="14"
      height="14"
      ><path
        d="M12 2a10 10 0 0 0-10 10 10 10 0 0 0 10 10 10 10 0 0 0 10-10A10 10 0 0 0 12 2Z"
      /><path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z" /></svg
    >
  </button>

  <button class="icon-btn" onclick={onToggleTheme} title={$t("Toggle theme")}>
    {#if theme === "dark"}
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.7"
        stroke-linecap="round"
        stroke-linejoin="round"
        width="14"
        height="14"
        ><circle cx="12" cy="12" r="4" /><path
          d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"
        /></svg
      >
    {:else}
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.7"
        stroke-linecap="round"
        stroke-linejoin="round"
        width="14"
        height="14"
        ><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" /></svg
      >
    {/if}
  </button>

  <button
    class="icon-btn"
    class:active={logOpen}
    onclick={onToggleLog}
    title={$t("Toggle log panel")}
  >
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.7"
      stroke-linecap="round"
      stroke-linejoin="round"
      width="16"
      height="16"><path d="M4 6h12M4 12h16M4 18h10" /></svg
    >
  </button>

  <button class="icon-btn" title={$t("Debug Routine")} onclick={onDebug}>
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.7"
      stroke-linecap="round"
      stroke-linejoin="round"
      width="16"
      height="16"
      ><path d="m8 2 1.88 1.88" /><path d="M14.12 3.88 16 2" /><path
        d="M9 7.13v-1a3.003 3.003 0 1 1 6 0v1"
      /><path
        d="M12 20c-3.31 0-6-2.69-6-6v-1h4v2h4v-2h4v1c0 3.31-2.69 6-6 6Z"
      /><path d="M6 13V9c0-3.31 2.69-6 6-6s6 2.69 6 6v4H6Z" /><path
        d="M2 13h4"
      /><path d="M18 13h4" /><path d="m4.5 18 2.5-2.5" /><path
        d="m17 15.5 2.5 2.5"
      /></svg
    >
  </button>

  <button class="icon-btn" title={$t("ADB Settings")} onclick={onAdbSettings}>
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.7"
      stroke-linecap="round"
      stroke-linejoin="round"
      width="16"
      height="16"
      ><rect x="5" y="2" width="14" height="20" rx="2" ry="2" /><path
        d="M12 18h.01"
      /></svg
    >
  </button>

  <button class="icon-btn" title={$t("Game Settings")} onclick={onGameSettings}>
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.7"
      stroke-linecap="round"
      stroke-linejoin="round"
      width="16"
      height="16"
      ><line x1="6" y1="12" x2="10" y2="12"></line><line
        x1="8"
        y1="10"
        x2="8"
        y2="14"
      ></line><line x1="15" y1="13" x2="15.01" y2="13"></line><line
        x1="18"
        y1="11"
        x2="18.01"
        y2="11"
      ></line><rect x="2" y="6" width="20" height="12" rx="2"></rect></svg
    >
  </button>

  <button class="icon-btn" title={$t("App settings")} onclick={onAppSettings}>
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.7"
      stroke-linecap="round"
      stroke-linejoin="round"
      width="16"
      height="16"
      ><circle cx="12" cy="12" r="3" /><path
        d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"
      /></svg
    >
  </button>
</div>

<style>
  .status-bar {
    height: 44px;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0 12px;
    border-bottom: 1px solid var(--line);
    background: var(--bg-1);
    flex: 0 0 44px;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .brand-name {
    font-size: 13px;
    font-weight: 600;
    letter-spacing: -0.01em;
  }

  .version {
    font-size: 11px;
    color: var(--text-4);
    font-family: var(--font-mono);
  }

  .divider {
    width: 1px;
    height: 20px;
    background: var(--line);
  }

  .profile-chip {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 10px 4px 8px;
    border-radius: 999px;
    background: var(--bg-2);
    border: 1px solid var(--line);
    font-size: 12px;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
  }

  .profile-name {
    font-weight: 600;
  }

  .sep,
  .sep-alt {
    color: var(--text-3);
  }

  .sep-alt {
    color: var(--text-4);
  }

  .device-id {
    color: var(--text-3);
    font-family: var(--font-mono);
    font-size: 11px;
  }

  .status-label {
    color: var(--text-3);
  }

  .spacer {
    flex: 1;
  }

  .active {
    background: var(--accent-ghost);
    color: var(--accent);
  }
</style>
