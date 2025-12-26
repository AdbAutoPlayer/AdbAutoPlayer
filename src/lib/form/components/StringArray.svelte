<script lang="ts">
  import { showErrorToast } from "$lib/toast/toast-error";
  import type { StringValueArrayProps } from "$lib/form/types";

  let {
    value = $bindable(),
    minItems,
  }: StringValueArrayProps = $props();

  function addItem() {
    value = [...value, ""];
  }

  function removeItem(idx: number) {
    if (minItems && value.length <= minItems) {
      showErrorToast(`Minimum ${minItems} items required`);
      return;
    }
    value = value.toSpliced(idx, 1);
  }
</script>

<div class="flex flex-col gap-2">
  {#each value as item, idx}
    <div class="flex items-center gap-2">
      <input type="text" class="input w-full" bind:value={value[idx]} />

      {#if !minItems || idx >= minItems}
        <button
          type="button"
          class="btn preset-filled-error-100-900 btn-sm"
          onclick={() => removeItem(idx)}
        >
          –
        </button>
      {/if}
    </div>
  {/each}

  <button
    type="button"
    class="btn preset-filled-primary-100-900 btn-sm"
    onclick={addItem}
  >
    + Add
  </button>

  {#if minItems && value.length < minItems}
    <p class="text-error text-sm">
      At least {minItems} items required.
    </p>
  {/if}
</div>
