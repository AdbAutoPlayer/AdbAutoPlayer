<script lang="ts">
  import { updateCheckboxArray } from "$lib/checkboxHelper";
  import { t } from "$lib/i18n/i18n";
  import NoOptionsAvailable from "../Components/NoOptionsAvailable.svelte";

  let {
    constraint,
    value = $bindable(),
    name,
  }: {
    constraint: ImageCheckboxConstraint;
    value: string[];
    name: string;
  } = $props();

  function sanitizeForImage(value: string): string {
    return value.toLowerCase().replace(/\s+/g, "") + ".png";
  }

  const choicesWithImages: Array<string> = $derived(
    constraint.choices?.map((choice) => sanitizeForImage(choice)),
  );

  function handleCheckboxChange(choice: string, isChecked: boolean) {
    value = updateCheckboxArray(value, choice, isChecked);
  }
</script>

<div class="flex flex-wrap gap-2.5">
  {#if choicesWithImages.length > 0}
    {#each constraint.choices as choice, i}
      <label class="badge flex items-center bg-surface-950 p-4">
        <input
          class="checkbox"
          type="checkbox"
          {name}
          value={choice}
          checked={Array.isArray(value) ? value.includes(choice) : false}
          onchange={(e) =>
            handleCheckboxChange(choice, e.currentTarget.checked)}
        />
        <img
          src={`/imagecheckbox/${constraint.image_dir_path.replace(/\/$/, "")}/${choicesWithImages[i]}`}
          alt={choice}
          class="h-6 w-6"
        />
        <span>{$t(choice)}</span>
      </label>
    {/each}
  {:else}
    <NoOptionsAvailable />
  {/if}
</div>
