<script lang="ts">
  import { t } from "$lib/i18n/i18n";

  interface Props {
    collapsed: boolean;
    onAddProfile: () => void;
  }

  let { collapsed, onAddProfile }: Props = $props();
</script>

{#if !collapsed}
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
{/if}

<style>
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
    background: transparent;
    border: none;
    cursor: pointer;
  }

  .icon-btn-small:hover {
    background: var(--bg-hover);
    color: var(--text-1);
  }
</style>
