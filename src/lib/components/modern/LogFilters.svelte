<script lang="ts">
  import { t } from "$lib/i18n/i18n";

  interface Props {
    linesCount: number;
  }

  let { linesCount }: Props = $props();
</script>

<div class="filter-info">
  <span class="status-dot"></span>
  <div class="title">{$t("Live Log")}</div>
  <span class="spacer"></span>
  <span class="count">{linesCount} {$t("lines")}</span>
</div>

<style>
  .filter-info {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: var(--ok);
  }

  .title {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-3);
  }

  .spacer {
    flex: 1;
  }

  .count {
    font-size: 11px;
    color: var(--text-4);
    font-family: var(--font-mono);
  }
</style>
