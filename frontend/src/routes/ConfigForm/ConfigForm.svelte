<script lang="ts">
  import { onMount } from "svelte";
  import MultiCheckbox from "./MultiCheckbox.svelte";
  import ImageCheckbox from "./ImageCheckbox.svelte";

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
      if (isCheckboxConstraint(constraint)) {
        val = Boolean(value);
      }
      if (isNumberConstraint(constraint)) {
        val = Number(value);
      }

      if (
        isImageCheckboxConstraint(constraint) ||
        isMultiCheckboxConstraint(constraint)
      ) {
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
          } else {
            console.log("processFormData unexpected type ", val);
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
    console.log("Should not happen: ");
    console.log(value);
    return [];
  }

  function isNumberConstraint(value: any): value is NumberConstraint {
    return (
      typeof value === "object" && value !== null && value.type === "number"
    );
  }

  function isMultiCheckboxConstraint(
    value: any,
  ): value is MultiCheckboxConstraint {
    return (
      typeof value === "object" &&
      value !== null &&
      value.type === "multicheckbox"
    );
  }

  function isImageCheckboxConstraint(
    value: any,
  ): value is ImageCheckboxConstraint {
    return (
      typeof value === "object" &&
      value !== null &&
      value.type === "imagecheckbox"
    );
  }

  function isCheckboxConstraint(value: any): value is CheckboxConstraint {
    return value.type === "checkbox";
  }

  function isSelectConstraint(value: any): value is SelectConstraint {
    return (
      typeof value === "object" && value !== null && value.type === "select"
    );
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
      console.error("Should not happen");
      return null;
    }
    return constraints[sectionKey][key].default_value;
  }

  function isTextConstraint(value: any): value is TextConstraint {
    return value.type === "text";
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
                {:else if isNumberConstraint(value)}
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
                {:else if isMultiCheckboxConstraint(value)}
                  <MultiCheckbox
                    constraint={value}
                    value={getStringArrayOrEmptyArray(
                      getValueOrDefault(sectionKey, key),
                    )}
                    name="{sectionKey}-{key}"
                  />
                {:else if isImageCheckboxConstraint(value)}
                  <ImageCheckbox
                    constraint={value}
                    value={getStringArrayOrEmptyArray(
                      getValueOrDefault(sectionKey, key),
                    )}
                    name="{sectionKey}-{key}"
                  />
                {:else if isSelectConstraint(value)}
                  <select
                    id="{sectionKey}-{key}"
                    name="{sectionKey}-{key}"
                    class="select w-full"
                  >
                    {#each value.choices as option}
                      <option
                        value={option}
                        selected={getValueOrDefault(sectionKey, key) === option}
                        >{option}</option
                      >
                    {/each}
                  </select>
                {:else if isTextConstraint(value)}
                  <input
                    type="text"
                    id="{sectionKey}-{key}"
                    name="{sectionKey}-{key}"
                    value={getValueOrDefault(sectionKey, key)}
                    class="input w-full"
                    {...value.regex ? { pattern: value.regex } : {}}
                    {...value.title ? { title: value.title } : {}}
                  />
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
