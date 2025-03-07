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
    const newConfig: { [key: string]: Record<string, any> } = JSON.parse(
      JSON.stringify(configObject),
    );

    for (const [sectionKey, sectionConfig] of Object.entries(newConfig)) {
      if (sectionKey === "plugin") continue;

      for (const key of Object.keys(sectionConfig)) {
        const inputName = `${sectionKey}-${key}`;
        const inputValues = formData.getAll(inputName);

        switch (typeof sectionConfig[key]) {
          case "boolean":
            sectionConfig[key] = formData.has(inputName);
            break;
          case "number":
            sectionConfig[key] = Number(formData.get(inputName));
            break;
          case "object":
            if (Array.isArray(sectionConfig[key])) {
              sectionConfig[key] = inputValues.map(String);
            }
            break;
          default:
            sectionConfig[key] = formData.get(inputName);
            break;
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

  function isSelectConstraint(value: any): value is SelectConstraint {
    return (
      typeof value === "object" && value !== null && value.type === "select"
    );
  }
</script>

<div class="h-full max-h-full overflow-y-auto">
  <h2 class="h2 pb-2 text-center text-2xl">Config</h2>

  <form id="config-form" class="config-form">
    {#each configSections as { sectionKey, sectionConfig }}
      <fieldset
        class="border-surface-900/60 rounded-container-token mb-4 border p-4"
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
                    checked={Boolean(configObject[sectionKey][key])}
                    class="checkbox"
                  />
                {:else if isNumberConstraint(value)}
                  <input
                    type="number"
                    id="{sectionKey}-{key}"
                    name="{sectionKey}-{key}"
                    value={configObject[sectionKey][key]}
                    min={value.minimum}
                    max={value.maximum}
                    step={value.step}
                    class="input w-full"
                  />
                {:else if isMultiCheckboxConstraint(value)}
                  <MultiCheckbox
                    choices={value.choices}
                    value={getStringArrayOrEmptyArray(
                      configObject[sectionKey][key],
                    )}
                    name="{sectionKey}-{key}"
                  />
                {:else if isImageCheckboxConstraint(value)}
                  <ImageCheckbox
                    choices={value.choices}
                    value={getStringArrayOrEmptyArray(
                      configObject[sectionKey][key],
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
                        selected={configObject[sectionKey][key] === option}
                        >{option}</option
                      >
                    {/each}
                  </select>
                {:else}
                  <input
                    type="text"
                    id="{sectionKey}-{key}"
                    name="{sectionKey}-{key}"
                    value={configObject[sectionKey][key]}
                    class="input w-full"
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
