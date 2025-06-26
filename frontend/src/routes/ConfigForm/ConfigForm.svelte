<script lang="ts">
  import { onMount } from "svelte";
  import { Accordion } from "@skeletonlabs/skeleton-svelte";
  import MultiCheckbox from "./MultiCheckbox.svelte";
  import ImageCheckbox from "./ImageCheckbox.svelte";
  import MyCustomRoutine from "./MyCustomRoutine.svelte";
  import { isConstraintOfType } from "$lib/utils/constraint";

  let {
    configObject,
    constraints,
    onConfigSave,
  }: {
    configObject: ConfigObject;
    constraints: Constraints;
    onConfigSave: (config: object) => void;
  } = $props();

  // Initialize the form state from configObject and constraints
  function initializeFormState() {
    const newFormState: Record<string, Record<string, any>> = {};

    for (const sectionKey in constraints) {
      newFormState[sectionKey] = {};

      for (const key in constraints[sectionKey]) {
        const constraint = constraints[sectionKey][key];
        if (Array.isArray(constraint)) {
          continue;
        }

        // Use existing config value if available, otherwise use default
        if (
          configObject &&
          configObject[sectionKey] &&
          key in configObject[sectionKey]
        ) {
          newFormState[sectionKey][key] = configObject[sectionKey][key];
        } else {
          newFormState[sectionKey][key] = constraint.default_value;
        }
      }
    }

    return newFormState;
  }

  let formState: Record<string, Record<string, any>> = $state(
    initializeFormState(),
  );

  const configSections: Array<{
    sectionKey: string;
    sectionConfig: ConstraintSection;
  }> = $derived(
    Object.entries(constraints).map(([sectionKey, sectionConfig]) => ({
      sectionKey,
      sectionConfig,
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
      "form.config-form",
    ) as HTMLFormElement;

    if (formElement && !formElement.checkValidity()) {
      formElement.reportValidity();
      return;
    }
    console.log(formState);

    // Create a deep copy of formState to pass to onConfigSave
    const configToSave = JSON.parse(JSON.stringify(formState));
    onConfigSave?.(configToSave);
  }

  function setupRealTimeValidation() {
    const formElement = document.getElementById(
      "config-form",
    ) as HTMLFormElement;
    if (!formElement) {
      console.error("Form element not found.");
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
    setupRealTimeValidation();
  });

  // Reinitialize when configObject or constraints change
  $effect(() => {
    if (configObject || constraints) {
      formState = initializeFormState();
    }
  });
</script>

<div class="h-full max-h-full overflow-y-auto">
  <form id="config-form" class="config-form">
    <Accordion multiple>
      {#each configSections as { sectionKey, sectionConfig }}
        <Accordion.Item value={sectionKey}>
          {#snippet control()}<span class="h5">{sectionKey}</span>{/snippet}
          {#snippet panel()}
            <div class="p-4">
              {#each Object.entries(sectionConfig) as [key, value]}
                <div class="mb-4">
                  <div class="flex items-center justify-between">
                    <label
                      for="{sectionKey}-{key}"
                      class="mr-3 w-40 text-right"
                    >
                      {key}
                    </label>

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
        onclick={handleSave}>Save</button
      >
    </div>
  </form>
</div>
