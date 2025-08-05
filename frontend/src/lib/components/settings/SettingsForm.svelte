<script lang="ts">
  import { onMount } from "svelte";
  import { Accordion } from "@skeletonlabs/skeleton-svelte";
  import MultiCheckbox from "./checkbox/MultiCheckbox.svelte";
  import ImageCheckbox from "./checkbox/ImageCheckbox.svelte";
  import MyCustomRoutine from "./MyCustomRoutine.svelte";
  import { isConstraintOfType } from "$lib/settings-form/constraint";
  import { t } from "$lib/i18n/i18n";
  import { showErrorToast } from "$lib/toast/toast-error";

  let {
    settings,
    constraints,
    onSettingsSave,
  }: {
    settings: SettingsObject;
    constraints: Constraints;
    onSettingsSave: (settings: object) => void;
  } = $props();

  let isSaving = $state(false);

  function initializeFormState() {
    const newFormState: Record<string, Record<string, any>> = {};

    for (const sectionKey in constraints) {
      if (sectionKey === "Order") {
        continue;
      }
      newFormState[sectionKey] = {};

      for (const key in constraints[sectionKey]) {
        const constraint = constraints[sectionKey][key];
        if (Array.isArray(constraint)) {
          continue;
        }
        if (settings && settings[sectionKey] && key in settings[sectionKey]) {
          newFormState[sectionKey][key] = settings[sectionKey][key];
        } else {
          newFormState[sectionKey][key] = constraint.default_value;
        }
      }
    }
    formState = newFormState;
  }

  let formState: Record<string, Record<string, any>> = $state({});

  const settingsSections: Array<{
    sectionKey: string;
    sectionSettings: ConstraintSection;
  }> = $derived(
    Object.entries(constraints)
      .filter(([sectionKey]) => sectionKey !== "Order")
      .map(([sectionKey, sectionSettings]) => ({
        sectionKey,
        sectionSettings: Object.fromEntries(
          Object.entries(sectionSettings).filter(([key]) => key !== "Order"),
        ),
      })),
  );

  function getInputType(sectionKey: string, key: string): string {
    const constraint = constraints[sectionKey]?.[key];
    if (
      typeof constraint === "object" &&
      constraint !== null &&
      "type" in constraint
    ) {
      return constraint.type;
    }
    return "text";
  }

  function handleSave(): void {
    // Basic validation - you can expand this as needed
    const formElement = document.querySelector(
      "form.settings-form",
    ) as HTMLFormElement;

    if (formElement && !formElement.checkValidity()) {
      formElement.reportValidity();
      return;
    }

    isSaving = true;

    const settingsToSave = JSON.parse(JSON.stringify(formState));
    Promise.resolve(onSettingsSave?.(settingsToSave)).finally(() => {
      isSaving = false;
    });
  }

  function setupRealTimeValidation() {
    const formElement = document.getElementById(
      "settings-form",
    ) as HTMLFormElement;
    if (!formElement) {
      showErrorToast("Settings Form not found.");
      return;
    }
    const inputs = formElement.querySelectorAll("input, select");
    inputs.forEach((input) => {
      input.addEventListener("input", () => {
        if (
          input instanceof HTMLInputElement ||
          input instanceof HTMLFormElement
        ) {
          if (!input.checkValidity()) {
            input.reportValidity();
          }
        }
      });
    });
  }

  onMount(() => {
    initializeFormState();
    setupRealTimeValidation();
  });
</script>

<div class="h-full max-h-full">
  <form id="settings-form" class="settings-form">
    <Accordion multiple>
      {#each settingsSections as { sectionKey, sectionSettings }}
        <Accordion.Item value={sectionKey}>
          {#snippet control()}<span class="h5">{$t(sectionKey)}</span>{/snippet}
          {#snippet panel()}
            <div class="p-4">
              {#each Object.entries(sectionSettings) as [key, value]}
                <div class="mb-4">
                  <div class="flex items-center justify-between">
                    {#if !isConstraintOfType(value, "MyCustomRoutine") && !isConstraintOfType(value, "multicheckbox")}
                      <label
                        for="{sectionKey}-{key}"
                        class="mr-3 w-40 text-right"
                      >
                        {$t(key)}
                      </label>
                    {/if}
                    <div class="flex flex-1 items-center">
                      {#if getInputType(sectionKey, key) === "checkbox"}
                        <input
                          type="checkbox"
                          id="{sectionKey}-{key}"
                          bind:checked={formState[sectionKey][key]}
                          class="checkbox"
                        />
                      {:else if isConstraintOfType(value, "number")}
                        <input
                          type="number"
                          id="{sectionKey}-{key}"
                          bind:value={formState[sectionKey][key]}
                          min={value.minimum}
                          max={value.maximum}
                          step={value.step}
                          class="input w-full"
                        />
                      {:else if isConstraintOfType(value, "multicheckbox")}
                        <MultiCheckbox
                          label={key}
                          constraint={value}
                          bind:value={formState[sectionKey][key]}
                          name="{sectionKey}-{key}"
                        />
                      {:else if isConstraintOfType(value, "imagecheckbox")}
                        <ImageCheckbox
                          constraint={value}
                          bind:value={formState[sectionKey][key]}
                          name="{sectionKey}-{key}"
                        />
                      {:else if isConstraintOfType(value, "select")}
                        <select
                          id="{sectionKey}-{key}"
                          bind:value={formState[sectionKey][key]}
                          class="select w-full"
                        >
                          {#each value.choices as option}
                            <option value={option}>
                              {option}
                            </option>
                          {/each}
                        </select>
                      {:else if isConstraintOfType(value, "text")}
                        <input
                          type="text"
                          id="{sectionKey}-{key}"
                          bind:value={formState[sectionKey][key]}
                          class="input w-full"
                          {...value.regex ? { pattern: value.regex } : {}}
                          {...value.title ? { title: value.title } : {}}
                        />
                      {:else if isConstraintOfType(value, "MyCustomRoutine")}
                        <MyCustomRoutine
                          constraint={value}
                          bind:value={formState[sectionKey][key]}
                          name="{sectionKey}-{key}"
                        />
                      {:else}
                        <p>
                          {Array.isArray(value)
                            ? "Value (array)"
                            : (value?.type ?? "Value")} cannot be displayed
                        </p>
                      {/if}
                    </div>
                  </div>
                </div>
              {/each}
            </div>
          {/snippet}
        </Accordion.Item>
        <hr class="hr" />
      {/each}
    </Accordion>

    <div class="m-4">
      <button
        type="button"
        class="btn preset-filled-primary-100-900 hover:preset-filled-primary-500"
        disabled={isSaving}
        onclick={handleSave}
      >
        {$t("Save")}
      </button>
    </div>
  </form>
</div>
