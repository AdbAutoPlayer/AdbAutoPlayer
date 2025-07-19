<script lang="ts">
  import type { MenuButton } from "$lib/settings-form/model";

  let {
    disabled,
    menuButton,
  }: {
    disabled: boolean;
    menuButton: MenuButton;
  } = $props();
  import { t } from "$lib/i18n/i18n";
</script>

<button
  type="button"
  {disabled}
  class="ph-autocapture btn w-auto max-w-[300px]"
  class:preset-filled-primary-100-900={!menuButton.isProcessRunning}
  class:hover:preset-filled-primary-500={!menuButton.isProcessRunning}
  class:preset-outlined-primary-100-900={menuButton.isProcessRunning}
  onclick={menuButton.callback}
  data-ph-capture-attribute-label={menuButton.option.label}
>
  {menuButton.option.custom_label
    ? menuButton.option.custom_label
    : $t(menuButton.option.label)}
</button>
