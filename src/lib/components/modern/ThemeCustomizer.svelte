<script lang="ts">
  import { t } from "$lib/i18n/i18n";
  import { ui } from "$lib/stores.svelte";
  import { fade, fly } from "svelte/transition";

  let { onClose }: { onClose: () => void } = $props();

  const presets = [
    { name: "Purple", h: 272 },
    { name: "Blue", h: 220 },
    { name: "Cyan", h: 185 },
    { name: "Green", h: 145 },
    { name: "Amber", h: 45 },
    { name: "Red", h: 25 },
    { name: "Rose", h: 350 },
  ];
</script>

<!-- Backdrop -->
<button
  class="backdrop"
  onclick={onClose}
  transition:fade={{ duration: 200 }}
  aria-label="Close customizer"
></button>

<div class="customizer-panel" transition:fly={{ x: 300, duration: 300 }}>
  <div class="panel-header">
    <h3>{$t("Customize Theme")}</h3>
    <button class="close-btn" onclick={onClose} aria-label="Close customizer">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        width="18"
        height="18"><path d="M18 6 6 18M6 6l12 12" /></svg
      >
    </button>
  </div>

  <div class="panel-body">
    <!-- Appearance -->
    <section class="section">
      <div class="section-label">{$t("Appearance")}</div>
      <div class="mode-toggle">
        <button
          class="mode-btn"
          class:active={ui.theme === "dark"}
          onclick={() => ui.setTheme("dark")}
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            width="14"
            height="14"
            ><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" /></svg
          >
          {$t("Dark")}
        </button>
        <button
          class="mode-btn"
          class:active={ui.theme === "light"}
          onclick={() => ui.setTheme("light")}
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            width="14"
            height="14"
            ><circle cx="12" cy="12" r="5" /><path
              d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
            /></svg
          >
          {$t("Light")}
        </button>
      </div>
    </section>

    <!-- Accent Color -->
    <section class="section">
      <div class="section-label">
        {$t("Accent Hue")} ({ui.accentHue}°)
      </div>
      <input
        type="range"
        min="0"
        max="360"
        value={ui.accentHue}
        oninput={(e) => ui.setAccentHue(Number(e.currentTarget.value))}
        class="hue-slider"
      />

      <div class="presets-grid">
        {#each presets as p}
          <button
            class="preset-btn"
            style="--p-color: oklch(0.67 0.18 {p.h})"
            class:active={ui.accentHue === p.h}
            onclick={() => ui.setAccentHue(p.h)}
            title={p.name}
          ></button>
        {/each}
      </div>
    </section>

    <div class="info-card">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        width="16"
        height="16"
        ><circle cx="12" cy="12" r="10" /><path d="M12 16v-4M12 8h.01" /></svg
      >
      <p>{$t("These settings are applied locally to your current session.")}</p>
    </div>
  </div>
</div>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(4px);
    z-index: 1000;
  }

  .customizer-panel {
    position: fixed;
    top: 44px;
    right: 0;
    bottom: 0;
    width: 320px;
    background: var(--bg-1);
    border-left: 1px solid var(--line);
    box-shadow: -8px 0 32px rgba(0, 0, 0, 0.2);
    z-index: 1001;
    display: flex;
    flex-direction: column;
  }

  .panel-header {
    padding: 18px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid var(--line-soft);
  }

  .panel-header h3 {
    margin: 0;
    font-size: 15px;
    font-weight: 700;
  }

  .close-btn {
    color: var(--text-3);
    transition: color var(--dur-1);
  }

  .close-btn:hover {
    color: var(--text-1);
  }

  .panel-body {
    flex: 1;
    overflow-y: auto;
    padding: 24px 20px;
    display: flex;
    flex-direction: column;
    gap: 32px;
  }

  .section-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-3);
    margin-bottom: 12px;
  }

  .mode-toggle {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    background: var(--bg-2);
    padding: 4px;
    border-radius: 10px;
    border: 1px solid var(--line);
  }

  .mode-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 8px;
    border-radius: 7px;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-3);
    transition: all var(--dur-1);
  }

  .mode-btn.active {
    background: var(--bg-1);
    color: var(--text-1);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .hue-slider {
    width: 100%;
    margin: 8px 0 16px;
    appearance: none;
    height: 6px;
    border-radius: 3px;
    background: linear-gradient(
      to right,
      oklch(0.67 0.18 0),
      oklch(0.67 0.18 60),
      oklch(0.67 0.18 120),
      oklch(0.67 0.18 180),
      oklch(0.67 0.18 240),
      oklch(0.67 0.18 300),
      oklch(0.67 0.18 360)
    );
  }

  .hue-slider::-webkit-slider-thumb {
    appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: white;
    border: 3px solid var(--accent);
    cursor: pointer;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
  }

  .presets-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(32px, 1fr));
    gap: 10px;
  }

  .preset-btn {
    aspect-ratio: 1;
    border-radius: 8px;
    background: var(--p-color);
    border: 2px solid transparent;
    transition: transform var(--dur-1);
  }

  .preset-btn:hover {
    transform: scale(1.1);
  }

  .preset-btn.active {
    border-color: var(--text-1);
    transform: scale(1.15);
  }

  .info-card {
    margin-top: auto;
    padding: 12px;
    background: var(--bg-2);
    border-radius: 10px;
    border: 1px solid var(--line-soft);
    display: flex;
    gap: 10px;
    color: var(--text-3);
    font-size: 11.5px;
    line-height: 1.4;
  }

  .info-card svg {
    flex-shrink: 0;
  }
</style>
