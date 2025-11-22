<script lang="ts">
  import { t } from "$lib/i18n/i18n";

  let {
    text,
  }: {
    text: string;
  } = $props();
</script>

<div class="space-y-2">
  <div class="flex items-center gap-4">
    <h4 class="h4 text-surface-800 dark:text-surface-100">
      {$t(text)}
    </h4>
  </div>
</div>
