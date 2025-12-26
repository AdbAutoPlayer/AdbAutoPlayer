<script lang="ts">
  import { Accordion } from "@skeletonlabs/skeleton-svelte";
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
            resolvedProps[propKey] = resolveRef(prop, settingsProps.formSchema);
          },
        );

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
      // console.log($state.snapshot(prop))
      const refName = prop.items.$ref.replace("#/$defs/", "");
      return {
        ...prop,
        items: rootSchema.$defs?.[refName] ?? prop.items,
      };
    }

    return prop;
  }

  function handleSave(): void {
    const formElement = document.querySelector(
      "form.settings-form",
    ) as HTMLFormElement;

    if (formElement && !formElement.checkValidity()) {
      formElement.reportValidity();
      return;
    }

    isSaving = true;
    onFormSubmit();
    isSaving = false;
  }

  function setupRealTimeValidation() {
    const formElement = document.getElementById(
      "schema-form",
    ) as HTMLFormElement;

    if (!formElement) {
      void showErrorToast("Form not found.");
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

    return () => {
      isSaving = false;
    };
  });
</script>

<div class="h-full max-h-full">
  <form id="schema-form" class="settings-form">
    <Accordion multiple>
      {#each sections as { key, schema }}
        <Accordion.Item value={key}>
          <Accordion.ItemTrigger class="flex items-center justify-between">
            <span class="px-2 py-1 h5">
              {$t(schema.title ?? key)}
            </span>

            <Accordion.ItemIndicator class="group flex items-center">
              <span class="hidden size-4 group-data-[state=open]:block">
                -
              </span>
              <span class="block size-4 group-data-[state=open]:hidden">
                +
              </span>
            </Accordion.ItemIndicator>
          </Accordion.ItemTrigger>
          <Accordion.ItemContent>
            <div class="p-4">
              {#each Object.entries(schema.properties ?? {}) as [propKey, prop]}
                {@const arraySchema = asArraySchema(prop)}
                {@const choices = asNonEmptyStringArray(prop)}
                <div class="mb-4 flex items-center justify-between">
                  {#if arraySchema && arraySchema.items.enum && Array.isArray(settingsProps.formData[key][propKey]) && choices}
                    {#if prop.formType === "TaskList"}
                      <TaskList
                          choices={choices}
                          bind:value={settingsProps.formData[key][propKey] as string[]}
                        />
                    {:else if prop.formType === "AlnumGroupedCheckboxArray"}
                      <AlnumGroupedCheckboxArray
                        title={$t(arraySchema.title ?? propKey)}
                        choices={choices}
                        bind:value={settingsProps.formData[key][propKey] as string[]}
                      />
                    {:else}
                      <label
                        for={`${key}-${propKey}`}
                        class="mr-3 w-40 text-right"
                      >
                        {$t(arraySchema.title ?? propKey)}
                      </label>

                      <div class="flex flex-1 items-center">
                        {#if arraySchema.formType === "ImageCheckboxArray"}
                          <ImageCheckboxArray
                            choices={choices}
                            assetPath={arraySchema.assetPath as string}
                            bind:value={settingsProps.formData[key][propKey] as string[]}
                          />
                        {:else}
                          <CheckboxArray
                            choices={choices}
                            bind:value={settingsProps.formData[key][propKey] as string[]}
                          />
                        {/if}
                      </div>
                    {/if}
                  {:else if arraySchema && arraySchema.items.type === "string" && Array.isArray(settingsProps.formData[key][propKey])}
                    <div class="w-full">
                      <StringArray
                        bind:value={settingsProps.formData[key][propKey] as string[]}
                        minItems={arraySchema.minItems}
                      />
                    </div>
                  {:else}
                    <label
                      for={`${key}-${propKey}`}
                      class="mr-3 w-40 text-right"
                    >
                      {$t(prop.title ?? propKey)}
                    </label>

                    <div class="flex flex-1 items-center">
                      {#if prop.enum}
                        <!-- Dropdown for enum -->
                        <select
                          id={`${key}-${propKey}`}
                          class="select w-full"
                          bind:value={settingsProps.formData[key][propKey]}
                        >
                          {#each prop.enum as option}
                            <option value={option}>{$t(String(option))}</option>
                          {/each}
                        </select>
                      {:else if prop.type === "boolean"}
                        <!-- Checkbox -->
                        <input
                          id={`${key}-${propKey}`}
                          type="checkbox"
                          class="checkbox"
                          bind:checked={
                            () => Boolean(settingsProps.formData[key][propKey]),
                            (v) => (settingsProps.formData[key][propKey] = v)
                          }
                        />
                      {:else if prop.type === "integer" || prop.type === "number"}
                        <!-- Numeric input -->
                        <input
                          id={`${key}-${propKey}`}
                          type="number"
                          class="input w-full"
                          min={prop.minimum}
                          max={prop.maximum}
                          step={prop.step ??
                            (prop.type === "integer" ? 1 : "any")}
                          bind:value={settingsProps.formData[key][propKey]}
                        />
                      {:else}
                        <!-- Default text input -->
                        <input
                          id={`${key}-${propKey}`}
                          type="text"
                          class="input w-full"
                          bind:value={settingsProps.formData[key][propKey]}
                          {...prop.regex ? { pattern: prop.regex } : {}}
                          {...prop.title ? { title: prop.title } : {}}
                        />
                      {/if}
                    </div>
                  {/if}
                </div>
              {/each}
            </div>
          </Accordion.ItemContent>
        </Accordion.Item>
        <hr class="hr" />
      {/each}
    </Accordion>
    <div class="m-4">
      <button
        type="button"
        class="btn w-full preset-filled-primary-100-900 hover:preset-filled-primary-500"
        disabled={isSaving}
        onclick={handleSave}
      >
        {$t("Save")}
      </button>
    </div>
  </form>
</div>
