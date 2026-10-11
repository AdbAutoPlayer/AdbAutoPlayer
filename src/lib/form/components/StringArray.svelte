<script lang="ts">
  import { showErrorToast } from "#lib/toast/toast-error.ts";
  import type { StringValueArrayProps } from "#lib/form/types.ts";
  import { t } from "#lib/i18n/i18n.ts";

  let { value = $bindable(), minItems }: StringValueArrayProps = $props();

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

<div class="array-container">
  {#each value as item, idx}
    <div class="array-item">
      <input type="text" class="form-input" bind:value={value[idx]} />

      {#if !minItems || value.length > (minItems || 0)}
        <button
          type="button"
          class="remove-btn"
          onclick={() => removeItem(idx)}
          title="Remove"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.5"
            stroke-linecap="round"
            stroke-linejoin="round"
            width="14"
            height="14"><path d="M18 6 6 18M6 6l12 12" /></svg
          >
        </button>
      {/if}
    </div>
  {/each}

  <button type="button" class="add-btn" onclick={addItem}>
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2.5"
      stroke-linecap="round"
      stroke-linejoin="round"
      width="14"
      height="14"><path d="M12 5v14M5 12h14" /></svg
    >
    <span>{$t("Add Item")}</span>
  </button>

  {#if minItems && value.length < minItems}
    <p class="error-text">
      {$t("At least {{count}} items required.", { count: String(minItems) })}
    </p>
  {/if}
</div>

<style>
  .array-container {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-top: 4px;
  }

  .array-item {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .remove-btn {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: grid;
    place-items: center;
    background: var(--err-ghost);
    color: var(--err);
    transition: all var(--dur-1);
    flex: 0 0 32px;
  }

  .remove-btn:hover {
    background: var(--err);
    color: white;
  }

  .add-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 8px;
    border-radius: 8px;
    background: var(--bg-3);
    border: 1px dashed var(--line);
    color: var(--text-2);
    font-size: 12px;
    font-weight: 600;
    transition: all var(--dur-1);
    margin-top: 4px;
    width: 100%;
  }

  .add-btn:hover {
    background: var(--bg-2);
    border-color: var(--accent);
    color: var(--accent);
  }

  .error-text {
    font-size: 11px;
    color: var(--err);
    font-weight: 500;
  }
</style>
