<script lang="ts">
  import { t } from "$lib/i18n/i18n";
  import { updateCheckboxArray } from "$lib/form/checkboxHelper";

  let {
    choices,
    value = $bindable(),
  }: {
    choices: Array<any>;
    value: Array<any>;
  } = $props();

  function handleCheckboxChange(choice: string, isChecked: boolean) {
    value = updateCheckboxArray(value, choice, isChecked);
  }
</script>

<div class="flex flex-wrap gap-2.5">
  {#each choices as choice}
    <label class="m-0.5 flex items-center">
      <input
        type="checkbox"
        class="mr-0.5 ml-0.25 checkbox"
        value={choice}
        checked={value.includes(choice)}
        onchange={(e) => handleCheckboxChange(choice, e.currentTarget.checked)}
      />
      <span class="mr-0.25">{$t(choice)}</span>
    </label>
  {/each}
</div>
