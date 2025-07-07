<script lang="ts">
  import { updateCheckboxArray } from "$lib/checkboxHelper";
  import { t } from "$lib/i18n/i18n";
  import SettingsSectionHeader from "../Components/SettingsSectionHeader.svelte";

  let {
    label,
    constraint,
    value = $bindable(),
    name,
  }: {
    label: string;
    constraint: MultiCheckboxConstraint;
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

  const groupedOptions = groupOptionsByFirstLetter(constraint.choices || []);

  function handleCheckboxChange(choice: string, isChecked: boolean) {
    value = updateCheckboxArray(value, choice, isChecked);
  }
</script>

<div class="space-y-6">
  <div
    class="flex items-center justify-between rounded-xl bg-gradient-to-r from-primary-50 to-secondary-50 p-4 shadow-lg dark:from-primary-900/20 dark:to-secondary-900/20"
  >
    <SettingsSectionHeader text={label} />
  </div>

  <div class="flex flex-wrap gap-2.5">
    {#if groupedOptions.size <= 0}
      <p>{$t("No options available")}</p>
    {:else if constraint.group_alphabetically}
      {#each [...groupedOptions.entries()] as [letter, options]}
        <div class="flex-1 rounded border border-white/20 p-1.25">
          <div class="mb-1.25 bg-white/10 p-0.5 font-bold">
            {letter}
          </div>
          <div class="flex flex-col">
            {#each options as option}
              <label class="m-1 flex items-center text-left">
                <input
                  type="checkbox"
                  class="mr-1.5 ml-0.25 checkbox"
                  {name}
                  value={option}
                  checked={Array.isArray(value)
                    ? value.includes(option)
                    : false}
                  onchange={(e) =>
                    handleCheckboxChange(option, e.currentTarget.checked)}
                />
                <span class="mr-0.25">{$t(option)}</span>
              </label>
            {/each}
          </div>
        </div>
      {/each}
    {:else}
      {#each constraint.choices as choice}
        <label class="m-0.5 flex items-center">
          <input
            type="checkbox"
            class="mr-0.5 ml-0.25 checkbox"
            {name}
            value={choice}
            checked={Array.isArray(value) ? value.includes(choice) : false}
            onchange={(e) =>
              handleCheckboxChange(choice, e.currentTarget.checked)}
          />
          <span class="mr-0.25">{$t(choice)}</span>
        </label>
      {/each}
    {/if}
  </div>
</div>
