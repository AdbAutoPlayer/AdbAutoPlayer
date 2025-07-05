<script lang="ts">
  let {
    disabled,
    label,
    isProcessRunning,
    callback,
  }: {
    disabled: boolean;
    label: string;
    isProcessRunning: boolean;
    callback: () => void;
  } = $props();
  import { t } from "$lib/i18n/i18n";
</script>

<button
  type="button"
  {disabled}
  class="ph-autocapture btn w-auto max-w-[300px]"
  class:preset-filled-primary-100-900={!isProcessRunning}
  class:hover:preset-filled-primary-500={!isProcessRunning}
  class:preset-outlined-primary-100-900={isProcessRunning}
  onclick={callback}
>
  {$t(label)}
</button>
