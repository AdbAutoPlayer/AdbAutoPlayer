<script lang="ts">
  import { t } from "$lib/i18n/i18n";
  import { updateCheckboxArray } from "$lib/form/checkboxHelper";
  import NoOptionsAvailable from "$lib/components/generic/NoOptionsAvailable.svelte";

  let {
    choices,
    assetPath,
    value = $bindable(),
  }: {
    choices: Array<any>;
    assetPath: string;
    value: Array<any>;
  } = $props();

  function handleCheckboxChange(choice: string, isChecked: boolean) {
    value = updateCheckboxArray(value, choice, isChecked);
  }
</script>

<div class="flex flex-wrap gap-2.5">
  {#if choices.length > 0}
    {#each choices as choice}
      <label class="badge flex items-center bg-surface-950 p-4">
        <input
          class="checkbox"
          type="checkbox"
          value={choice}
          checked={Array.isArray(value) ? value.includes(choice) : false}
          onchange={(e) =>
            handleCheckboxChange(choice, e.currentTarget.checked)}
        />
        <img src={`${assetPath}/${choice}.png`} alt={choice} class="h-6 w-6" />
        <span>{$t(choice)}</span>
      </label>
    {/each}
  {:else}
    <NoOptionsAvailable />
  {/if}
</div>
