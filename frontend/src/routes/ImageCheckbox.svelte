<script lang="ts">
  let {
    choices,
    value,
    name,
  }: {
    choices: string[];
    value: string[];
    name: string;
  } = $props();

  function sanitizeForImage(value: string): string {
    return value.toLowerCase().replace(/\s+/g, "") + ".png";
  }

  const choicesWithImages: Array<string> = $derived(
    choices?.map((choice) => sanitizeForImage(choice)),
  );
</script>

<div class="flex flex-wrap gap-2.5">
  {#if choicesWithImages.length > 0}
    {#each choices as choice, i}
      <label class="badge bg-surface-950 flex items-center p-4">
        <input
          class="checkbox"
          type="checkbox"
          {name}
          value={choice}
          checked={Array.isArray(value) ? value.includes(choice) : false}
        />
        <img
          src={"/imagecheckbox/" + choicesWithImages[i]}
          alt={choice}
          class="w-6 h-6"
        />
        <span>{choice}</span>
      </label>
    {/each}
  {:else}
    <p>No options available</p>
  {/if}
</div>
