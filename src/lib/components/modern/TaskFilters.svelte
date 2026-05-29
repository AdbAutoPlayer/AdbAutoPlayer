<script lang="ts">
  import { t } from "$lib/i18n/i18n";
  import { ui } from "$lib/stores.svelte";

  interface Props {
    query: string;
  }

  let { query = $bindable() }: Props = $props();
</script>

<div class="toolbar">
  <div class="search-box">
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.7"
      stroke-linecap="round"
      stroke-linejoin="round"
      width="14"
      height="14"
      class="search-icon"
      ><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg
    >
    <input
      bind:value={query}
      placeholder={$t("Search tasks...")}
      class="search-input"
    />
    <kbd class="kbd">⌘K</kbd>
  </div>

  <div class="variant-toggle">
    {#each [{ id: "cards", label: $t("Cards"), icon: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z" }, { id: "palette", label: $t("Palette"), icon: "M8 6h13M8 12h13M8 18h13M4 6h.01M4 12h.01M4 18h.01" }, { id: "accordion", label: $t("Accordion"), icon: "M3 4h18v6H3zM3 14h18v6H3z" }] as v}
      <button
        class="v-btn"
        class:active={ui.taskViewVariant === v.id}
        onclick={() => ui.setTaskViewVariant(v.id as any)}
        title={v.label}
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
        >
          <path d={v.icon} />
        </svg>
        <span>{v.label}</span>
      </button>
    {/each}
  </div>
</div>

<style>
  .toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 20px;
    margin-top: 18px;
  }

  .search-box {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 10px;
    border-radius: 10px;
    flex: 1;
    background: var(--bg-1);
    border: 1px solid var(--line);
  }

  .search-icon {
    color: var(--text-3);
  }

  .search-input {
    flex: 1;
    background: transparent;
    border: 0;
    outline: 0;
    color: var(--text-1);
    font-size: 13px;
    font-family: inherit;
  }

  .kbd {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-3);
    padding: 2px 6px;
    border: 1px solid var(--line);
    border-radius: 4px;
    background: var(--bg-2);
  }

  .variant-toggle {
    display: flex;
    padding: 2px;
    border-radius: 10px;
    background: var(--bg-1);
    border: 1px solid var(--line);
  }

  .v-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 10px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 500;
    background: transparent;
    color: var(--text-3);
    transition: all var(--dur-1);
    cursor: pointer;
  }

  .v-btn.active {
    background: var(--bg-3);
    color: var(--text-1);
  }
</style>
