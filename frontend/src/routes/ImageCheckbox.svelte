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

<div class="imagecheckbox">
  {#if choicesWithImages.length > 0}
    {#each choices as choice, i}
      <label class="checkbox-container">
        <input
          type="checkbox"
          {name}
          value={choice}
          checked={Array.isArray(value) ? value.includes(choice) : false}
        />
        <img
          src={"/imagecheckbox/" + choicesWithImages[i]}
          alt={choice}
          class="choice-icon"
        />
        <span>{choice}</span>
      </label>
    {/each}
  {:else}
    <p>No options available</p>
  {/if}
</div>

<style>
  .imagecheckbox {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .checkbox-container {
    display: flex;
    align-items: center;
    gap: 10px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 4px;
    padding: 5px;
    background-color: rgba(255, 255, 255, 0.1);
  }

  .choice-icon {
    width: 24px;
    height: 24px;
    object-fit: contain;
    border-radius: 4px;
  }

  input[type="checkbox"] {
    margin: 0;
  }

  span {
    font-size: 14px;
  }
</style>
