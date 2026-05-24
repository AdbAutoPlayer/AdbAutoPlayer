<script lang="ts">
  import { t } from "$lib/i18n/i18n";

  interface Props {
    collapsed: boolean;
    profilesLength: number;
    runningCount: number;
  }

  let { collapsed, profilesLength, runningCount }: Props = $props();
</script>

{#if !collapsed}
  <div class="footer">
    <span>{profilesLength} {$t("profiles")}</span>
    <span class="mono">{runningCount} {$t("running")}</span>
  </div>
{/if}

<style>
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
</style>
