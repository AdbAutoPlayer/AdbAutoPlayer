<script lang="ts">
  import { t } from "$lib/i18n/i18n";
  import { onMount } from "svelte";
  import { showErrorToast } from "$lib/toast/toast-error";
  import type { JSONSchema } from "json-schema-to-typescript";
  import CheckboxArray from "$lib/form/components/CheckboxArray.svelte";
  import ImageCheckboxArray from "$lib/form/components/ImageCheckboxArray.svelte";
  import AlnumGroupedCheckboxArray from "$lib/form/components/AlnumGroupedCheckboxArray.svelte";
  import TaskList from "$lib/form/components/TaskList.svelte";
  import type { SettingsProps } from "$lib/menu/model";
  import StringArray from "$lib/form/components/StringArray.svelte";
  import { asArraySchema, asNonEmptyStringArray } from "$lib/form/types";

  let {
    settingsProps = $bindable(),
    onFormSubmit,
  }: {
    settingsProps: SettingsProps;
    onFormSubmit: () => void;
  } = $props();

  let isSaving = $state(false);
  let openSections = $state(new Set<string>());

  interface Section {
    key: string;
    schema: JSONSchema;
  }

  let sections: Section[] = $derived.by(() => {
    return Object.entries(settingsProps.formSchema.properties ?? {})
      .map(([key, value]) => {
        if (!("$ref" in value)) return null;

        const defName = value.$ref?.replace("#/$defs/", "");
        if (!defName) return null;

        const sectionSchema = settingsProps.formSchema.$defs?.[defName];
        if (!sectionSchema) return null;

        const resolvedProps: Record<string, any> = {};
        Object.entries(sectionSchema.properties ?? {}).forEach(
          ([propKey, prop]) => {
            if (propKey === "theme") return;
            resolvedProps[propKey] = resolveRef(prop, settingsProps.formSchema);
          },
        );

        if (Object.keys(resolvedProps).length === 0) return null;

        return {
          key,
          schema: {
            ...sectionSchema,
            title: value.title ?? sectionSchema.title,
            properties: resolvedProps,
          },
        };
      })
      .filter(Boolean) as Section[];
  });

  function resolveRef(prop: any, rootSchema: JSONSchema) {
    if ("$ref" in prop && typeof prop.$ref === "string") {
      const refName = prop.$ref.replace("#/$defs/", "");
      return rootSchema.$defs?.[refName] ?? prop;
    }

    if (prop.type === "array" && prop.items?.$ref) {
      const refName = prop.items.$ref.replace("#/$defs/", "");
      return {
        ...prop,
        items: rootSchema.$defs?.[refName] ?? prop.items,
      };
    }

    return prop;
  }

  async function handleSave(): Promise<void> {
    const formElement = document.getElementById(
      "schema-form",
    ) as HTMLFormElement;

    if (formElement && !formElement.checkValidity()) {
      formElement.reportValidity();
      return;
    }

    isSaving = true;
    void (async () => {
      await onFormSubmit();
      isSaving = false;
    })();
  }

  function toggleSection(key: string) {
    if (openSections.has(key)) {
      openSections.delete(key);
    } else {
      openSections.add(key);
    }
    openSections = new Set(openSections);
  }

  onMount(() => {
    // Open the first section by default
    if (sections.length > 0) {
      openSections.add(sections[0].key);
    }
    return () => {
      isSaving = false;
    };
  });
</script>

<div class="schema-form-container">
  <form
    id="schema-form"
    class="settings-form"
    onsubmit={(e) => e.preventDefault()}
  >
    <div class="sections-list">
      {#each sections as { key, schema }}
        {@const isOpen = openSections.has(key)}
        <div class="form-section" class:open={isOpen}>
          <button
            type="button"
            class="section-header"
            onclick={() => toggleSection(key)}
          >
            <span class="section-title">{$t(schema.title ?? key)}</span>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              width="14"
              height="14"
              class="chevron"
              style="transform: {isOpen ? 'rotate(180deg)' : 'rotate(0)'}"
            >
              <path d="m6 9 6 6 6-6" />
            </svg>
          </button>

          {#if isOpen}
            <div class="section-content">
              {#each Object.entries(schema.properties ?? {}) as [propKey, prop]}
                {@const arraySchema = asArraySchema(prop)}
                {@const choices = asNonEmptyStringArray(prop)}

                <div class="field-row">
                  {#if arraySchema && arraySchema.items.enum && Array.isArray(settingsProps.formData[key]?.[propKey]) && choices}
                    {#if prop.formType === "TaskList"}
                      <TaskList
                        {choices}
                        bind:value={settingsProps.formData[key][propKey] as any}
                      />
                    {:else if prop.formType === "AlnumGroupedCheckboxArray"}
                      <AlnumGroupedCheckboxArray
                        title={$t(arraySchema.title ?? propKey)}
                        {choices}
                        bind:value={settingsProps.formData[key][propKey] as any}
                      />
                    {:else}
                      <!-- svelte-ignore a11y_label_has_associated_control -->
                      <label class="field-label"
                        >{$t(arraySchema.title ?? propKey)}</label
                      >
                      <div class="field-control">
                        {#if arraySchema.formType === "ImageCheckboxArray"}
                          <ImageCheckboxArray
                            {choices}
                            assetPath={arraySchema.assetPath as string}
                            bind:value={
                              settingsProps.formData[key][propKey] as any
                            }
                          />
                        {:else}
                          <CheckboxArray
                            {choices}
                            bind:value={
                              settingsProps.formData[key][propKey] as any
                            }
                          />
                        {/if}
                      </div>
                    {/if}
                  {:else if arraySchema && arraySchema.items.type === "string" && Array.isArray(settingsProps.formData[key]?.[propKey])}
                    <div class="full-width-field">
                      <!-- svelte-ignore a11y_label_has_associated_control -->
                      <label class="field-label-alt"
                        >{$t(arraySchema.title ?? propKey)}</label
                      >
                      <StringArray
                        bind:value={settingsProps.formData[key][propKey] as any}
                        minItems={arraySchema.minItems}
                      />
                    </div>
                  {:else}
                    <label for={`${key}-${propKey}`} class="field-label">
                      {$t(prop.title ?? propKey)}
                    </label>

                    <div class="field-control">
                      {#if prop.enum}
                        <select
                          id={`${key}-${propKey}`}
                          class="select"
                          bind:value={settingsProps.formData[key][propKey]}
                        >
                          {#each prop.enum as option}
                            <option value={option}>{$t(String(option))}</option>
                          {/each}
                        </select>
                      {:else if prop.type === "boolean"}
                        <label class="toggle-switch">
                          <input
                            id={`${key}-${propKey}`}
                            type="checkbox"
                            bind:checked={
                              () =>
                                Boolean(settingsProps.formData[key]?.[propKey]),
                              (v) => (settingsProps.formData[key][propKey] = v)
                            }
                          />
                          <span class="slider"></span>
                        </label>
                      {:else if prop.type === "integer" || prop.type === "number"}
                        {#if prop.formType === "slider"}
                          <div class="slider-container">
                            <input
                              id={`${key}-${propKey}`}
                              type="range"
                              class="range-input"
                              min={prop.minimum}
                              max={prop.maximum}
                              step={prop.multipleOf ??
                                (prop.type === "integer" ? 1 : 0.1)}
                              bind:value={settingsProps.formData[key][propKey]}
                            />
                            <span class="range-value"
                              >{settingsProps.formData[key][propKey]}</span
                            >
                          </div>
                        {:else}
                          <input
                            id={`${key}-${propKey}`}
                            type="number"
                            class="input"
                            min={prop.minimum}
                            max={prop.maximum}
                            step={prop.multipleOf ??
                              (prop.type === "integer" ? 1 : "any")}
                            bind:value={settingsProps.formData[key][propKey]}
                          />
                        {/if}
                      {:else}
                        <input
                          id={`${key}-${propKey}`}
                          type="text"
                          class="input"
                          bind:value={settingsProps.formData[key][propKey]}
                          {...prop.regex ? { pattern: prop.regex } : {}}
                          {...prop.htmlTitle ? { title: prop.htmlTitle } : {}}
                        />
                      {/if}
                    </div>
                  {/if}
                </div>
              {/each}
            </div>
          {/if}
        </div>
      {/each}
    </div>

    <div class="form-footer">
      <button
        type="button"
        class="save-btn"
        disabled={isSaving}
        onclick={handleSave}
      >
        {#if isSaving}
          <span class="spinner"></span>
        {/if}
        {$t("Save Settings")}
      </button>
    </div>
  </form>
</div>

<style>
  .schema-form-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--bg-1);
  }

  .settings-form {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .sections-list {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .form-section {
    border-radius: 12px;
    background: var(--bg-1);
    border: 1px solid var(--line);
    overflow: hidden;
    transition: all var(--dur-1);
  }

  .form-section.open {
    border-color: var(--line-hi);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .section-header {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 18px;
    background: var(--bg-2);
    border-bottom: 1px solid transparent;
    transition: all var(--dur-1);
  }

  .form-section.open .section-header {
    border-bottom-color: var(--line);
    background: var(--bg-1);
  }

  .section-title {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.02em;
    color: var(--text-2);
  }

  .chevron {
    color: var(--text-4);
    transition: transform var(--dur-1);
  }

  .section-content {
    padding: 18px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .field-row {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .field-label {
    flex: 0 0 140px;
    font-size: 12px;
    font-weight: 500;
    color: var(--text-3);
    text-align: right;
  }

  .field-label-alt {
    display: block;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-3);
    margin-bottom: 8px;
  }

  .field-control {
    flex: 1;
    min-width: 0;
  }

  .full-width-field {
    width: 100%;
  }

  .form-footer {
    padding: 16px;
    border-top: 1px solid var(--line);
    background: var(--bg-2);
  }

  .save-btn {
    width: 100%;
    padding: 12px;
    border-radius: 10px;
    background: var(--accent);
    color: white;
    font-weight: 700;
    font-size: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    transition: all var(--dur-1);
    box-shadow: 0 4px 12px color-mix(in oklab, var(--accent) 25%, transparent);
  }

  .save-btn:hover:not(:disabled) {
    filter: brightness(1.1);
    transform: translateY(-1px);
  }

  .save-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .select option {
    background-color: var(--bg-1);
    color: var(--text-1);
  }

  .select:focus option {
    background-color: var(--bg-1);
  }

  .toggle-switch {
    position: relative;
    display: inline-block;
    width: 36px;
    height: 20px;
  }

  .toggle-switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .slider {
    position: absolute;
    cursor: pointer;
    inset: 0;
    background-color: var(--bg-3);
    transition: 0.3s;
    border-radius: 20px;
    border: 1px solid var(--line);
  }

  .slider:before {
    position: absolute;
    content: "";
    height: 14px;
    width: 14px;
    left: 2px;
    bottom: 2px;
    background-color: var(--text-4);
    transition: 0.3s;
    border-radius: 50%;
  }

  input:checked + .slider {
    background-color: var(--accent-ghost);
    border-color: var(--accent);
  }

  input:checked + .slider:before {
    transform: translateX(16px);
    background-color: var(--accent);
  }

  .spinner {
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .slider-container {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
  }

  .range-input {
    flex: 1;
    appearance: none;
    height: 6px;
    border-radius: 3px;
    background: var(--bg-3);
    border: 1px solid var(--line);
    outline: none;
  }

  .range-input::-webkit-slider-thumb {
    appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--accent);
    cursor: pointer;
    border: 2px solid white;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    transition: transform 0.1s;
  }

  .range-input::-webkit-slider-thumb:hover {
    transform: scale(1.1);
  }

  .range-value {
    min-width: 32px;
    font-size: 12px;
    font-weight: 700;
    color: var(--text-2);
    text-align: right;
  }
</style>
