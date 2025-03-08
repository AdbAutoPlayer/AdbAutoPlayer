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
      <div class="rounded border border-white/20 p-1.25">
        <div class="mb-1.25 bg-white/10 p-0.5 font-bold">
          {letter}
        </div>
        <div class="flex flex-col">
          {#each options as option}
            <label class="m-0.5 flex items-center">
              <input
                type="checkbox"
                class="mr-0.5 ml-0.25 checkbox"
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
