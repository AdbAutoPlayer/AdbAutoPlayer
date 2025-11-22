<script lang="ts">
  import { t } from "$lib/i18n/i18n";
  import { updateCheckboxArray } from "$lib/form/checkboxHelper";
  import SettingsSectionHeader from "$lib/components/form/SettingsSectionHeader.svelte";
  import NoOptionsAvailable from "$lib/components/generic/NoOptionsAvailable.svelte";
  import IconX from "$lib/components/icons/feather/IconX.svelte";

  let {
    title,
    choices,
    value = $bindable(),
  }: {
    title: string;
    choices: Array<any>;
    value: Array<any>;
  } = $props();

  function groupOptionsByFirstCharacter(
    options: string[],
  ): Map<string, Array<{ original: string; translated: string }>> {
    // First, create array of objects with original and translated values
    const translatedOptions = options.map((option) => ({
      original: option,
      translated: $t(option),
    }));

    // Sort by translated text using locale-aware sorting
    translatedOptions.sort((a, b) => a.translated.localeCompare(b.translated));

    // Group by first character of translated text
    return translatedOptions.reduce((acc, option) => {
      const firstChar = option.translated.charAt(0).toUpperCase();
      if (!acc.has(firstChar)) {
        acc.set(firstChar, []);
      }
      acc.get(firstChar)!.push(option);
      return acc;
    }, new Map<string, Array<{ original: string; translated: string }>>());
  }

  let groupedOptions = $derived(
    groupOptionsByFirstCharacter(choices || []),
  );

  function handleCheckboxChange(choice: string, isChecked: boolean) {
    value = updateCheckboxArray(value, choice, isChecked);
  }
</script>

<div class="mx-auto flex w-full max-w-6xl flex-col gap-8 p-6">
  <div class="space-y-6">
    <div
      class="flex items-center justify-between rounded-xl bg-gradient-to-r from-primary-50 to-secondary-50 p-4 shadow-lg dark:from-primary-900/20 dark:to-secondary-900/20"
    >
      <SettingsSectionHeader text={$t(title)} />
    </div>
  {#if choices.length === 0}
    <NoOptionsAvailable />
  {:else}
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
                    value={option.original}
                    checked={value.includes(option.original)}
                    onchange={(e) =>
                handleCheckboxChange(option.original, e.currentTarget.checked)}
                  />
                  <span class="mr-0.25 break-keep">{option.translated}</span>
                </label>
              {/each}
            </div>
          </div>
        {/each}
      </div>
  {/if}
  </div>
</div>
