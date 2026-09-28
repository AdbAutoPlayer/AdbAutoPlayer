<script lang="ts">
  import { t } from "$lib/i18n/i18n";
  import type { MenuButton } from "$lib/menu/model";
  import { ui } from "$lib/stores.svelte";

  interface Props {
    b: MenuButton;
    disableActions: boolean;
    variant: "cards" | "palette" | "accordion";
  }

  let { b, disableActions, variant }: Props = $props();

  const isHidden = $derived(ui.isTaskHidden(b.taskKey));
</script>

{#snippet hideButton()}
  {#if b.taskKey}
    {@const key = b.taskKey}
    <button
      class="hide-btn"
      class:palette={variant === "palette"}
      onclick={() => ui.toggleTaskHidden(key)}
      title={isHidden ? $t("Show task") : $t("Hide task")}
      aria-label={isHidden ? $t("Show task") : $t("Hide task")}
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
        width="13"
        height="13"
      >
        {#if isHidden}
          <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" /><circle
            cx="12"
            cy="12"
            r="3"
          />
        {:else}
          <path
            d="M9.9 4.24A9.1 9.1 0 0 1 12 4c6.5 0 10 8 10 8a18.5 18.5 0 0 1-2.16 3.19M6.6 6.6A18.4 18.4 0 0 0 2 12s3.5 8 10 8a9.3 9.3 0 0 0 5.4-1.6M1 1l22 22"
          />
        {/if}
      </svg>
    </button>
  {/if}
{/snippet}

<div class="task-wrap" class:is-hidden={isHidden}>
  {#if variant === "palette"}
    <button
      class="palette-item"
      class:active={b.isProcessRunning}
      disabled={disableActions && !b.isProcessRunning && !b.alwaysEnabled}
      onclick={b.callback}
    >
      <span class="item-icon">
        {#if b.isProcessRunning}
          <span class="dot"></span>
        {:else}
          <svg viewBox="0 0 24 24" fill="currentColor" width="10" height="10"
            ><path d="M8 5v14l11-7z" /></svg
          >
        {/if}
      </span>
      <span class="item-label">{$t(b.option.label)}</span>
      {#if b.option.tooltip}
        <span class="item-hint">— {$t(b.option.tooltip)}</span>
      {/if}
      <div class="spacer"></div>
      {#if b.isProcessRunning}
        <span class="item-status">{$t("Running")}</span>
      {/if}
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
        width="14"
        height="14"
        class="chevron"><path d="m9 18 6-6-6-6" /></svg
      >
    </button>
  {:else}
    <button
      class="task-card"
      class:active={b.isProcessRunning}
      disabled={disableActions && !b.isProcessRunning && !b.alwaysEnabled}
      onclick={b.callback}
    >
      <div class="card-top">
        <div class="card-label">{$t(b.option.label)}</div>
        {#if b.isProcessRunning}
          <span class="running-tag">● {$t("Run")}</span>
        {:else}
          <div class="play-box">
            <svg viewBox="0 0 24 24" fill="currentColor" width="10" height="10"
              ><path d="M8 5v14l11-7z" /></svg
            >
          </div>
        {/if}
      </div>
      {#if b.option.tooltip && variant !== "accordion"}
        <div class="card-hint">{$t(b.option.tooltip)}</div>
      {/if}
    </button>
  {/if}
  {@render hideButton()}
</div>

<style>
  .task-wrap {
    position: relative;
  }

  .task-wrap.is-hidden {
    opacity: 0.55;
  }

  .hide-btn {
    position: absolute;
    right: 10px;
    bottom: 10px;
    width: 22px;
    height: 22px;
    border-radius: 6px;
    display: grid;
    place-items: center;
    background: var(--bg-2);
    color: var(--text-3);
    border: 1px solid var(--line);
    opacity: 0;
    transition: opacity var(--dur-1);
    cursor: pointer;
  }

  .hide-btn.palette {
    right: 40px;
    bottom: auto;
    top: 50%;
    transform: translateY(-50%);
  }

  .task-wrap:hover .hide-btn,
  .task-wrap.is-hidden .hide-btn,
  .hide-btn:focus-visible {
    opacity: 1;
  }

  .hide-btn:hover {
    color: var(--text-1);
  }
  .task-card {
    position: relative;
    padding: 14px;
    border-radius: 12px;
    background: var(--bg-1);
    border: 1px solid var(--line);
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-height: 80px;
    transition:
      transform var(--dur-1),
      border-color var(--dur-1),
      background var(--dur-1);
    text-align: left;
    width: 100%;
    cursor: pointer;
  }

  .task-card:not(:disabled):hover {
    border-color: color-mix(in oklab, var(--accent) 30%, var(--line));
  }

  .task-card:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .task-card.active {
    background: color-mix(in oklab, var(--accent) 10%, var(--bg-1));
    border-color: color-mix(in oklab, var(--accent) 45%, transparent);
  }

  .card-top {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
    width: 100%;
  }

  .card-label {
    font-weight: 600;
    font-size: 13.5px;
    letter-spacing: -0.005em;
  }

  .running-tag {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--accent);
    background: var(--accent-ghost);
    padding: 3px 6px;
    border-radius: 4px;
    flex: 0 0 auto;
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  .play-box {
    width: 22px;
    height: 22px;
    border-radius: 6px;
    display: grid;
    place-items: center;
    background: var(--bg-2);
    color: var(--text-3);
  }

  .card-hint {
    font-size: 11.5px;
    color: var(--text-3);
    line-height: 1.45;
  }

  /* Palette View */
  .palette-item {
    display: flex;
    width: 100%;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    border-bottom: 1px solid var(--line-soft);
    background: transparent;
    text-align: left;
    transition: background var(--dur-1);
    cursor: pointer;
  }

  .task-wrap:last-child .palette-item {
    border-bottom: none;
  }

  .palette-item:not(:disabled):hover {
    background: var(--bg-2);
  }

  .palette-item:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .palette-item.active {
    background: var(--accent-ghost);
  }

  .item-icon {
    width: 22px;
    height: 22px;
    border-radius: 6px;
    display: grid;
    place-items: center;
    background: var(--bg-3);
    color: var(--text-3);
    flex: 0 0 auto;
  }

  .palette-item.active .item-icon {
    background: var(--accent);
    color: white;
  }

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 999px;
    background: white;
  }

  .item-label {
    font-weight: 600;
    font-size: 13px;
  }

  .item-hint {
    font-size: 11px;
    color: var(--text-3);
  }

  .spacer {
    flex: 1;
  }

  .item-status {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--accent);
    font-family: var(--font-mono);
  }

  .chevron {
    color: var(--text-4);
  }
</style>
