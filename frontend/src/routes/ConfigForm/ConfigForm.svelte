<script lang="ts">
  import { onMount } from "svelte";
  import MultiCheckbox from "./MultiCheckbox.svelte";
  import ImageCheckbox from "./ImageCheckbox.svelte";
  import MyCustomRoutine from "./MyCustomRoutine.svelte";
  import {
    isConstraintOfType,
    isArrayInputConstraint,
  } from "$lib/utils/constraint";

  let {
    configObject,
    constraints,
    onConfigSave,
  }: {
    configObject: ConfigObject;
    constraints: Constraints;
    onConfigSave: (config: object) => void;
  } = $props();

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

  function processFormData(formData: FormData): Record<string, any> {
    const newConfig: Record<string, any> = {};
    const newConfigInFormData: Record<string, any> = {};

    for (const sectionKey in constraints) {
      if (!newConfig[sectionKey]) {
        newConfig[sectionKey] = {};
        newConfigInFormData[sectionKey] = {};
      }
      for (const key in constraints[sectionKey]) {
        const constraint = constraints[sectionKey][key];
        if (Array.isArray(constraint)) {
          continue;
        }
        const defaultValue = constraint.default_value;
        if (Array.isArray(defaultValue)) {
          newConfig[sectionKey][key] = [];
        } else {
          newConfig[sectionKey][key] = constraint.default_value;
        }
        newConfigInFormData[sectionKey][key] = false;
      }
    }

    formData.forEach((value, key) => {
      const keys = key.split("-");
      newConfigInFormData[keys[0]][keys[1]] = true;
      let val: any = value;
      const constraint = constraints[keys[0]]?.[keys[1]];
      if (isConstraintOfType(constraint, "checkbox")) {
        val = Boolean(value);
      }
      if (isConstraintOfType(constraint, "number")) {
        val = Number(value);
      }
      if (isArrayInputConstraint(constraint)) {
        newConfig[keys[0]][keys[1]].push(val);
      } else {
        newConfig[keys[0]][keys[1]] = val;
      }
    });

    for (const sectionKey in constraints) {
      for (const key in constraints[sectionKey]) {
        if (false === newConfigInFormData[sectionKey][key]) {
          const val = newConfig[sectionKey][key];
          if (typeof val === "boolean") {
            newConfig[sectionKey][key] = false;
          } else if (
            isArrayInputConstraint(constraints[sectionKey][key]) &&
            Array.isArray(val) &&
            val.length === 0
          ) {
            newConfig[sectionKey][key] = val;
          } else {
            console.log(
              `processFormData unexpected type for ${sectionKey}.${key}:`,
              val,
            );
          }
        }
      }
    }
    return newConfig;
  }

  function handleSave(): void {
    const formElement = document.querySelector(
      "form.config-form",
    ) as HTMLFormElement;

    if (!formElement.checkValidity()) {
      formElement.reportValidity();
      return;
    }

    const formData = new FormData(formElement);
    onConfigSave?.(processFormData(formData));
  }

  function setupRealTimeValidation() {
    const formElement = document.getElementById(
      "config-form",
    ) as HTMLFormElement;
    if (!formElement) {
      console.error("Form element not found.");
      return;
    }
    const inputs = formElement.querySelectorAll("input");
    inputs.forEach((input) => {
      input.addEventListener("input", () => {
        if (!input.checkValidity()) {
          input.reportValidity();
        }
      });
    });
  }

  onMount(() => {
    setupRealTimeValidation();
  });

  function getStringArrayOrEmptyArray(value: any): string[] {
    if (
      Array.isArray(value) &&
      value.every((item) => typeof item === "string")
    ) {
      return value as string[];
    }
    console.error(
      "Should not happen getStringArrayOrEmptyArray!",
      "isArray:",
      Array.isArray(value),
      "constructor:",
      value.constructor?.name,
      value,
    );
    return [];
  }

  function getValueOrDefault(sectionKey: string, key: string): any {
    if (
      configObject &&
      configObject[sectionKey] &&
      sectionKey in configObject &&
      key in configObject[sectionKey]
    ) {
      return configObject[sectionKey][key];
    }
    if (Array.isArray(constraints[sectionKey][key])) {
      console.error(
        "Should not happen getValueOrDefault!",
        "sectionKey:",
        sectionKey,
        "key:",
        key,
      );
      return null;
    }
    return constraints[sectionKey][key].default_value;
  }
</script>

<div class="h-full max-h-full overflow-y-auto">
  <form id="config-form" class="config-form">
    {#each configSections as { sectionKey, sectionConfig }}
      <fieldset
        class="rounded-container-token mb-4 border border-surface-900/60 p-4"
      >
        <legend class="px-2 text-xl">{sectionKey}</legend>

        {#each Object.entries(sectionConfig) as [key, value]}
          <div class="mb-4">
            <div class="flex items-center justify-between">
              <label for="{sectionKey}-{key}" class="mr-3 w-30 text-right">
                {key}
              </label>

              <div class="flex flex-1 items-center">
                {#if getInputType(sectionKey, key) === "checkbox"}
                  <input
                    type="checkbox"
                    id="{sectionKey}-{key}"
                    name="{sectionKey}-{key}"
                    checked={Boolean(getValueOrDefault(sectionKey, key))}
                    class="checkbox"
                  />
                {:else if isConstraintOfType(value, "number")}
                  <input
                    type="number"
                    id="{sectionKey}-{key}"
                    name="{sectionKey}-{key}"
                    value={getValueOrDefault(sectionKey, key)}
                    min={value.minimum}
                    max={value.maximum}
                    step={value.step}
                    class="input w-full"
                  />
                {:else if isConstraintOfType(value, "multicheckbox")}
                  <MultiCheckbox
                    constraint={value}
                    value={getStringArrayOrEmptyArray(
                      getValueOrDefault(sectionKey, key),
                    )}
                    name="{sectionKey}-{key}"
                  />
                {:else if isConstraintOfType(value, "imagecheckbox")}
                  <ImageCheckbox
                    constraint={value}
                    value={getStringArrayOrEmptyArray(
                      getValueOrDefault(sectionKey, key),
                    )}
                    name="{sectionKey}-{key}"
                  />
                {:else if isConstraintOfType(value, "select")}
                  <select
                    id="{sectionKey}-{key}"
                    name="{sectionKey}-{key}"
                    class="select w-full"
                  >
                    {#each value.choices as option}
                      <option
                        value={option}
                        selected={getValueOrDefault(sectionKey, key) === option}
                      >
                        {option}
                      </option>
                    {/each}
                  </select>
                {:else if isConstraintOfType(value, "text")}
                  <input
                    type="text"
                    id="{sectionKey}-{key}"
                    name="{sectionKey}-{key}"
                    value={getValueOrDefault(sectionKey, key)}
                    class="input w-full"
                    {...value.regex ? { pattern: value.regex } : {}}
                    {...value.title ? { title: value.title } : {}}
                  />
                {:else if isConstraintOfType(value, "MyCustomRoutine")}
                  <MyCustomRoutine
                    constraint={value}
                    value={getStringArrayOrEmptyArray(
                      getValueOrDefault(sectionKey, key),
                    )}
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
      </fieldset>
    {/each}

    <div class="m-4">
      <button
        type="button"
        class="btn preset-filled-primary-100-900 hover:preset-filled-primary-500"
        onclick={handleSave}>Save</button
      >
    </div>
  </form>
</div>
