<script lang="ts">
  import { t } from "$lib/i18n/i18n";
  import { profiles, settings, ui } from "$lib/stores.svelte";
  import { onMount, onDestroy } from "svelte";
  import type { MenuButton } from "$lib/menu/model";

  interface Props {
    onStop: () => void;
    activeTaskButton?: MenuButton;
  }

  let { onStop, activeTaskButton }: Props = $props();

  const profile = $derived(profiles.states[profiles.active]);
  const gameTitle = $derived(profile?.game_menu?.game_title);
  const activeTask = $derived(profile?.active_task);
  const displayTaskName = $derived(
    activeTaskButton?.option?.label ?? activeTask,
  );
  const deviceId = $derived(profile?.device_id);
  const profileName = $derived(
    settings.settings?.profiles?.profiles?.[profiles.active],
  );

  let startTime = $state<number | null>(null);
  let elapsed = $state("00:00");
  let timer: ReturnType<typeof setInterval>;

  $effect(() => {
    if (activeTask) {
      if (!startTime) {
        startTime = Date.now();
      }
    } else {
      startTime = null;
      elapsed = "00:00";
    }
  });

  function updateTimer() {
    if (!startTime) return;
    const s = Math.max(0, Math.floor((Date.now() - startTime) / 1000));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const ss = s % 60;
    const pad = (n: number) => String(n).padStart(2, "0");
    elapsed = h > 0 ? `${pad(h)}:${pad(m)}:${pad(ss)}` : `${pad(m)}:${pad(ss)}`;
  }

  onMount(() => {
    timer = setInterval(updateTimer, 1000);
  });

  onDestroy(() => {
    clearInterval(timer);
  });
</script>

{#if !activeTask}
  <!-- Calm idle hero -->
  <div class="hero-idle" class:compact={ui.taskViewVariant === "accordion"}>
    <div class="icon-idle">
      <svg viewBox="0 0 24 24" fill="currentColor" width="12" height="12"
        ><path d="M13 2 4 14h7l-1 8 9-12h-7l1-8Z" /></svg
      >
    </div>
    <div class="content">
      <div class="meta">
        {gameTitle ? $t(gameTitle) : $t("No game detected")}
      </div>
      <div class="title">
        {gameTitle
          ? $t("Pick a task to begin")
          : $t("Start any supported game")}
      </div>
      <div class="status">
        {deviceId
          ? `${profileName || "Profile"} · ${deviceId}`
          : $t("No device connected — check ADB settings")}
      </div>
    </div>
  </div>
{:else}
  <!-- Loud running hero -->
  <div class="hero-running" class:compact={ui.taskViewVariant === "accordion"}>
    <!-- moving stripes bg -->
    <div class="stripes" aria-hidden="true"></div>

    <div class="inner">
      <div class="status-icon">
        <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14"
          ><path d="M8 5v14l11-7z" /></svg
        >
        <span class="ring"></span>
      </div>

      <div class="main-info">
        <div class="tag-row">
          <span class="tag">● {$t("Running")}</span>
          <span class="game-name">{$t(gameTitle || "")}</span>
        </div>
        <div class="task-name">
          {displayTaskName}
        </div>
        <div class="stats">
          <div class="stat">
            <div class="stat-label">{$t("elapsed")}</div>
            <div class="stat-value big">{elapsed}</div>
          </div>
          <div class="stat">
            <div class="stat-label">{$t("device")}</div>
            <div class="stat-value">{deviceId}</div>
          </div>
          <div class="stat">
            <div class="stat-label">{$t("profile")}</div>
            <div class="stat-value">{profileName}</div>
          </div>
        </div>
      </div>

      <button class="stop-btn" onclick={onStop}>
        <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14"
          ><rect x="6" y="6" width="12" height="12" rx="2" /></svg
        >
        {$t("Stop Task")}
      </button>
    </div>
  </div>
{/if}

<style>
  .hero-idle {
    margin: 18px 20px 0;
    padding: 22px;
    border-radius: var(--radius-lg);
    background: var(--bg-1);
    border: 1px solid var(--line);
    display: flex;
    align-items: center;
    gap: 18px;
  }

  .icon-idle {
    width: 52px;
    height: 52px;
    border-radius: 12px;
    background: linear-gradient(135deg, var(--bg-3), var(--bg-2));
    display: grid;
    place-items: center;
    color: var(--text-3);
    border: 1px solid var(--line);
  }

  .content {
    flex: 1;
    min-width: 0;
  }

  .meta {
    font-size: 11px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-3);
    font-weight: 600;
    margin-bottom: 4px;
  }

  .title {
    font-size: 20px;
    font-weight: 600;
    letter-spacing: -0.015em;
  }

  .status {
    color: var(--text-3);
    margin-top: 4px;
    font-size: 12px;
  }

  .hero-running {
    margin: 18px 20px 0;
    padding: 22px;
    border-radius: var(--radius-lg);
    background:
      radial-gradient(
        120% 140% at 0% 0%,
        color-mix(in oklab, var(--accent) 22%, transparent) 0%,
        transparent 55%
      ),
      linear-gradient(180deg, var(--bg-2), var(--bg-1));
    border: 1px solid color-mix(in oklab, var(--accent) 35%, var(--line));
    box-shadow: var(--shadow);
    position: relative;
    overflow: hidden;
  }

  .stripes {
    position: absolute;
    inset: 0;
    opacity: 0.08;
    pointer-events: none;
    background-image: repeating-linear-gradient(
      135deg,
      var(--accent) 0 2px,
      transparent 2px 14px
    );
    animation: slide 14s linear infinite;
  }

  .inner {
    position: relative;
    display: flex;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
  }

  .status-icon {
    width: 64px;
    height: 64px;
    border-radius: 14px;
    background: linear-gradient(135deg, var(--accent-hi), var(--accent-lo));
    display: grid;
    place-items: center;
    color: white;
    box-shadow: 0 8px 24px color-mix(in oklab, var(--accent) 30%, transparent);
    position: relative;
    flex: 0 0 64px;
  }

  .ring {
    position: absolute;
    inset: -4px;
    border-radius: 18px;
    border: 2px solid color-mix(in oklab, var(--accent) 50%, transparent);
    animation: ringpulse 2s ease-out infinite;
  }

  .main-info {
    flex: 1 1 240px;
    min-width: 0;
  }

  .tag-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
    flex-wrap: wrap;
  }

  .tag {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--accent);
    background: var(--accent-ghost);
    padding: 3px 8px;
    border-radius: 999px;
  }

  .game-name {
    font-size: 11px;
    color: var(--text-3);
    font-weight: 500;
  }

  .task-name {
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1.15;
    word-break: break-word;
  }

  .stats {
    display: flex;
    gap: 22px;
    margin-top: 10px;
    font-size: 12px;
    color: var(--text-3);
    font-family: var(--font-mono);
    flex-wrap: wrap;
  }

  .stat-label {
    font-size: 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-4);
  }

  .stat-value {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-1);
    margin-top: 2px;
  }

  .stat-value.big {
    font-size: 18px;
    font-weight: 600;
  }

  .stop-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    border-radius: 10px;
    font-weight: 600;
    font-size: 13px;
    color: white;
    background: var(--err);
    box-shadow: 0 6px 14px color-mix(in oklab, var(--err) 30%, transparent);
    transition:
      filter var(--dur-1),
      transform var(--dur-1);
    flex: 0 0 auto;
    margin-left: auto;
  }

  .stop-btn:hover {
    filter: brightness(1.08);
  }

  /* Compact Mode Styles */
  .hero-idle.compact {
    margin: 12px 20px 0;
    padding: 12px 18px;
    gap: 14px;
  }
  .hero-idle.compact .icon-idle {
    width: 32px;
    height: 32px;
    border-radius: 8px;
  }
  .hero-idle.compact .icon-idle svg {
    width: 14px;
    height: 14px;
  }
  .hero-idle.compact .title {
    font-size: 15px;
  }
  .hero-idle.compact .meta {
    font-size: 10px;
    margin-bottom: 2px;
  }
  .hero-idle.compact .status {
    font-size: 11px;
    margin-top: 2px;
  }

  .hero-running.compact {
    margin: 12px 20px 0;
    padding: 12px 18px;
  }
  .hero-running.compact .status-icon {
    width: 36px;
    height: 36px;
    flex: 0 0 36px;
    border-radius: 10px;
  }
  .hero-running.compact .ring {
    inset: -2px;
    border-radius: 12px;
  }
  .hero-running.compact .task-name {
    font-size: 16px;
  }
  .hero-running.compact .stats {
    gap: 14px;
    margin-top: 6px;
  }
  .hero-running.compact .stat-value.big {
    font-size: 14px;
  }
  .hero-running.compact .stop-btn {
    padding: 6px 12px;
    font-size: 12px;
  }
</style>
