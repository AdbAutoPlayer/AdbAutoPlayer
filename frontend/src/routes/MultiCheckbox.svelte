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

  function groupOptionsByFirstLetter(options: string[]): Map<string, string[]> {
    return options.reduce((acc, option) => {
      const firstLetter = option.charAt(0).toUpperCase();
      if (!acc.has(firstLetter)) {
        acc.set(firstLetter, []);
      }
      acc.get(firstLetter)!.push(option);
      return acc;
    }, new Map<string, string[]>());
  }

  const groupedOptions = groupOptionsByFirstLetter(choices || []);
</script>

<div class="flex flex-wrap gap-2.5">
  {#if groupedOptions.size > 0}
    {#each [...groupedOptions.entries()] as [letter, options]}
      <div class="border border-white/20 rounded p-1.25">
        <div class="font-bold mb-1.25 bg-white/10 p-0.5">
          {letter}
        </div>
        <div class="flex flex-col">
          {#each options as option}
            <label class="flex items-center m-0.5">
              <input
                type="checkbox"
                class="checkbox ml-0.25 mr-0.5"
                {name}
                value={option}
                checked={Array.isArray(value) ? value.includes(option) : false}
              />
              <span class="mr-0.25">{option}</span>
            </label>
          {/each}
        </div>
      </div>
    {/each}
  {:else}
    <p>No options available</p>
  {/if}
</div>
