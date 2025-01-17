<script lang="ts">
  import { onMount } from "svelte";
  import MultiCheckbox from "./MultiCheckbox.svelte";

  let {
    configObject,
    constraints,
    onConfigSave,
  }: {
    configObject: Record<string, any>;
    constraints: Record<string, any>;
    onConfigSave: (config: object) => void;
  } = $props();

  const configSections: Array<Record<string, any>> = $derived(
    Object.entries(configObject)
      .filter(([key]) => key !== "plugin")
      .map(([sectionKey, sectionConfig]) => ({
        sectionKey,
        sectionConfig,
      })),
  );

  function getInputType(sectionKey: string, key: string): string {
    const constraint = constraints[sectionKey]?.[key];
    return constraint?.type ?? "text";
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

  function formatSectionKey(sectionKey: string): string {
    const withSpaces = sectionKey.replace(/_/g, " ");
    return withSpaces.replace(/\b\w/g, (match) => match.toUpperCase());
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
</script>

<form class="config-form" id="config-form">
  {#each configSections as { sectionKey, sectionConfig }}
    <fieldset>
      <legend>{formatSectionKey(sectionKey)}</legend>

      {#each Object.entries(sectionConfig) as [key, value]}
        <div class="form-group">
          <div class="form-group-inner">
            <label for="{sectionKey}-{key}">
              {formatSectionKey(key)}
            </label>

            <div class="input-container">
              {#if getInputType(sectionKey, key) === "checkbox"}
                <input
                  type="checkbox"
                  id="{sectionKey}-{key}"
                  name="{sectionKey}-{key}"
                  checked={Boolean(value)}
                />
              {:else if getInputType(sectionKey, key) === "number"}
                <input
                  type="number"
                  id="{sectionKey}-{key}"
                  name="{sectionKey}-{key}"
                  {value}
                  min={constraints[sectionKey]?.[key]?.minimum ?? 1}
                  max={constraints[sectionKey]?.[key]?.maximum ?? 999}
                />
              {:else if getInputType(sectionKey, key) === "multicheckbox"}
                <MultiCheckbox
                  choices={constraints[sectionKey]?.[key]?.choices || []}
                  value={getStringArrayOrEmptyArray(value)}
                  name="{sectionKey}-{key}"
                />
              {:else if getInputType(sectionKey, key) === "select"}
                <select id="{sectionKey}-{key}" name="{sectionKey}-{key}">
                  {#each constraints[sectionKey]?.[key]?.choices as option}
                    <option value={option} selected={value === option}
                      >{option}</option
                    >
                  {/each}
                </select>
              {:else}
                <input
                  type="text"
                  id="{sectionKey}-{key}"
                  name="{sectionKey}-{key}"
                  {value}
                />
              {/if}
            </div>
          </div>
        </div>
      {/each}
    </fieldset>
    <br />
  {/each}

  <button type="button" onclick={handleSave}>Save</button>
</form>

<style>
  fieldset {
    border-color: #0f0f0f98;
  }

  .form-group {
    margin-bottom: 15px;
  }

  .form-group-inner {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .form-group .form-group-inner label {
    flex: 0 0 120px;
    margin-right: 10px;
    text-align: right;
  }

  .input-container {
    flex: 1;
    display: flex;
    align-items: center;
  }

  .input-container input:not([type="checkbox"]) {
    width: 100%;
  }

  .input-container select {
    width: 100%;
  }

  .input-container input[type="checkbox"] {
    margin: 2px;
  }
</style>
