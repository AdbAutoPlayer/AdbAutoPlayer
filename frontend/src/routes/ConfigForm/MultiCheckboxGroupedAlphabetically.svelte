<script lang="ts">
  import { t } from "$lib/i18n/i18n";
  import { updateCheckboxArray } from "$lib/checkboxHelper";

  export let constraint: MultiCheckboxConstraint;
  export let value: string[];
  export let name: string;

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

  const groupedOptions = groupOptionsByFirstLetter(constraint.choices || []);

  function handleCheckboxChange(choice: string, isChecked: boolean) {
    value = updateCheckboxArray(value, choice, isChecked);
  }
</script>

<div class="flex flex-wrap gap-2.5">
  {#each [...groupedOptions.entries()] as [letter, options]}
    <div
      class="min-w-[calc(100%/var(--max-cols)-1.25rem)] flex-1 rounded border border-white/20 p-1.25"
    >
      <div class="mb-1.25 bg-white/10 p-0.5 font-bold">{letter}</div>
      <div class="flex flex-col">
        {#each options as option}
          <label class="m-1 flex items-center text-left">
            <input
              type="checkbox"
              class="mr-1.5 ml-0.25 checkbox"
              {name}
              value={option}
              checked={value.includes(option)}
              onchange={(e) =>
                handleCheckboxChange(option, e.currentTarget.checked)}
            />
            <span class="mr-0.25">{$t(option)}</span>
          </label>
        {/each}
      </div>
    </div>
  {/each}
</div>
