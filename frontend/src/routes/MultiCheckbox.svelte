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

  function groupOptionsByFirstLetter(
    options: string[],
  ): Record<string, string[]> {
    return options.reduce((acc: Record<string, string[]>, option: string) => {
      const firstLetter = option.charAt(0).toUpperCase();
      if (!acc[firstLetter]) {
        acc[firstLetter] = [];
      }
      acc[firstLetter].push(option);
      return acc;
    }, {});
  }

  const groupedOptions = groupOptionsByFirstLetter(choices || []);
</script>

<div class="multicheckbox-grouped">
  {#if Object.keys(groupedOptions).length > 0}
    {#each Object.entries(groupedOptions) as [letter, options]}
      <div class="letter-group">
        <div class="letter-header">{letter}</div>
        <div class="letter-options">
          {#each options as option}
            <label class="checkbox-container">
              <input
                type="checkbox"
                {name}
                value={option}
                checked={Array.isArray(value) ? value.includes(option) : false}
              />
              {option}
            </label>
          {/each}
        </div>
      </div>
    {/each}
  {:else}
    <p>No options available</p>
  {/if}
</div>

<style>
  .multicheckbox-grouped {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .letter-group {
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 4px;
    padding: 5px;
  }

  .letter-header {
    font-weight: bold;
    margin-bottom: 5px;
    text-align: center;
    background-color: rgba(255, 255, 255, 0.1);
    padding: 2px;
  }

  .letter-options {
    display: flex;
    flex-direction: column;
  }

  .checkbox-container {
    display: flex;
    align-items: center;
    margin: 2px 0;
  }
</style>
