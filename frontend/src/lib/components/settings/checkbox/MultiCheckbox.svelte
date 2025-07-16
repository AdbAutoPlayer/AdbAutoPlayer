<script lang="ts">
  import SettingsSectionHeader from "$lib/components/settings/SettingsSectionHeader.svelte";
  import NoOptionsAvailable from "$lib/components/generic/NoOptionsAvailable.svelte";
  import MultiCheckboxGroupedAlphabetically from "./MultiCheckboxGroupedAlphabetically.svelte";
  import MultiCheckboxDefault from "./MultiCheckboxDefault.svelte";
  import { t } from "$lib/i18n/i18n";

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
</script>

<div class="space-y-6">
  <div
    class="flex items-center justify-between rounded-xl bg-gradient-to-r from-primary-50 to-secondary-50 p-4 shadow-lg dark:from-primary-900/20 dark:to-secondary-900/20"
  >
    <SettingsSectionHeader text={$t(label)} />
  </div>

  {#if constraint.choices?.length <= 0}
    <NoOptionsAvailable />
  {:else if constraint.group_alphabetically}
    <MultiCheckboxGroupedAlphabetically {constraint} bind:value {name} />
  {:else}
    <MultiCheckboxDefault {constraint} bind:value {name} />
  {/if}
</div>
