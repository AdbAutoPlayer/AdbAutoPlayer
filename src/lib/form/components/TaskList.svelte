<script lang="ts">
  import IconX from "$lib/components/icons/feather/IconX.svelte";
  import { t } from "$lib/i18n/i18n";
  import SettingsSectionHeader from "./SettingsSectionHeader.svelte";
  import NoOptionsAvailable from "$lib/components/generic/NoOptionsAvailable.svelte";
  import type { TaskItem, TaskListProps } from "$lib/form/types";

  let { choices, value = $bindable() }: TaskListProps = $props();

  let draggedItem = $state<string | null>(null);
  let draggedFromSelected = $state(false);
  let draggedIndex = $state(-1);
  let currentDragPosition = $state<
    "above-first" | "between" | "below-last" | null
  >(null);
  let isOverContainer = $state(false);

  function handleDragStart(
    e: DragEvent,
    task: string,
    fromSelected: boolean,
    index: number = -1,
  ) {
    draggedItem = task;
    draggedFromSelected = fromSelected;
    draggedIndex = index;
    if (e.dataTransfer) {
      e.dataTransfer.effectAllowed = fromSelected ? "move" : "copy";
      e.dataTransfer.setData("text/plain", task);
    }
    currentDragPosition = null;
    isOverContainer = false;
  }

  let dropIndicatorPos = $state<{
    index: number;
    position: "before" | "after";
  } | null>(null);

  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    if (!draggedItem) return;

    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = draggedFromSelected ? "move" : "copy";
    }

    const container = e.currentTarget as HTMLElement;
    const items = container.querySelectorAll('[draggable="true"]');

    if (items.length === 0) {
      dropIndicatorPos = null;
      currentDragPosition = null;
      isOverContainer = true;
      return;
    }

    // Check if dragging above first item
    const firstItemRect = items[0].getBoundingClientRect();
    if (e.clientY < firstItemRect.top + firstItemRect.height * 0.25) {
      dropIndicatorPos = { index: 0, position: "before" };
      currentDragPosition = "above-first";
      isOverContainer = true;
      return;
    }

    // Check if dragging below last item
    const lastItemRect = items[items.length - 1].getBoundingClientRect();
    if (e.clientY > lastItemRect.bottom - lastItemRect.height * 0.25) {
      dropIndicatorPos = { index: items.length - 1, position: "after" };
      currentDragPosition = "below-last";
      isOverContainer = true;
      return;
    }

    // Check between items
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      const rect = item.getBoundingClientRect();
      const middleY = rect.top + rect.height / 2;

      if (e.clientY < middleY) {
        dropIndicatorPos = { index: i, position: "before" };
        currentDragPosition = "between";
        isOverContainer = true;
        return;
      } else if (e.clientY < rect.bottom) {
        dropIndicatorPos = { index: i, position: "after" };
        currentDragPosition = "between";
        isOverContainer = true;
        return;
      }
    }

    dropIndicatorPos = null;
    currentDragPosition = null;
    isOverContainer = true;
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    if (!draggedItem) return;

    // If we're not over the container, don't do anything
    if (!isOverContainer) {
      resetDragState();
      return;
    }

    // Handle empty list
    if (value.length === 0) {
      if (!draggedFromSelected) {
        value = [{ name: draggedItem, repeat: true }];
      }
      resetDragState();
      return;
    }

    let insertIndex = value.length;

    if (dropIndicatorPos) {
      const { index, position } = dropIndicatorPos;
      insertIndex = position === "before" ? index : index + 1;
    } else if (currentDragPosition === "above-first") {
      insertIndex = 0;
    } else if (currentDragPosition === "below-last") {
      insertIndex = value.length;
    }

    // Clamp insert index to valid range
    insertIndex = Math.max(0, Math.min(insertIndex, value.length));

    if (draggedFromSelected) {
      // Don't do anything if dropping on itself
      if (
        draggedIndex === insertIndex ||
        (draggedIndex + 1 === insertIndex && insertIndex < value.length)
      ) {
        resetDragState();
        return;
      }

      const newValue = [...value];
      const [movedItem] = newValue.splice(draggedIndex, 1);

      // Adjust insert index if we're moving downward in the array
      const adjustedIndex =
        draggedIndex < insertIndex ? insertIndex - 1 : insertIndex;
      newValue.splice(adjustedIndex, 0, movedItem);
      value = newValue;
    } else {
      // Adding from available tasks
      const newValue = [...value];
      newValue.splice(insertIndex, 0, { name: draggedItem, repeat: true });
      value = newValue;
    }

    resetDragState();
  }

  function resetDragState() {
    dropIndicatorPos = null;
    draggedItem = null;
    draggedFromSelected = false;
    draggedIndex = -1;
    currentDragPosition = null;
    isOverContainer = false;
  }

  function handleDragLeave(e: DragEvent) {
    const container = e.currentTarget as HTMLElement;
    const relatedTarget = e.relatedTarget as HTMLElement | null;

    if (!relatedTarget || !container.contains(relatedTarget)) {
      isOverContainer = false;
      // Don't reset the drag state completely here, just mark as not over container
      dropIndicatorPos = null;
      currentDragPosition = null;
    }
  }

  function handleContainerDragOver(e: DragEvent, index: number) {
    e.preventDefault();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = draggedFromSelected ? "move" : "copy";
    }

    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const middleY = rect.top + rect.height / 2;
    dropIndicatorPos = {
      index,
      position: e.clientY < middleY ? "before" : "after",
    };
    currentDragPosition = "between";
    isOverContainer = true;
  }

  function removeTask(index: number) {
    value = value.filter((_, i) => i !== index);
  }

  function clearList() {
    if (confirm($t("Are you sure you want to clear all tasks?"))) {
      value = [];
    }
  }

  function addTask(taskName: string) {
    value = [...value, { name: taskName, repeat: true }];
  }

  function toggleRepeat(index: number) {
    const newValue = [...value];
    newValue[index] = { ...newValue[index], repeat: !newValue[index].repeat };
    value = newValue;
  }
</script>

<div class="mx-auto flex w-full max-w-6xl flex-col gap-8 p-6">
  <div class="space-y-6">
    <div
      class="from-primary-50 to-secondary-50 dark:from-primary-900/20 dark:to-secondary-900/20 flex items-center justify-between rounded-xl bg-gradient-to-r p-4 shadow-lg"
    >
      <SettingsSectionHeader text={$t("Tasks")} />
      {#if choices.length > 0}
        <button
          class="btn rounded-lg bg-red-800 px-4 py-2 font-medium text-red-100 shadow-md transition-all duration-200 hover:scale-105 hover:bg-red-600 hover:text-white hover:shadow-lg"
          type="button"
          onclick={clearList}
        >
          {$t("Clear Tasks")}
        </button>
      {/if}
    </div>
    {#if choices.length === 0}
      <NoOptionsAvailable />
    {:else}
      <div class="grid grid-cols-1 gap-x-8 gap-y-4 md:grid-cols-2">
        <div class="contents md:contents">
          <div class="space-y-2">
            <div class="flex items-center gap-3">
              <div
                class="from-tertiary-500 to-tertiary-600 h-1 w-8 rounded-full bg-gradient-to-r"
              ></div>
              <h3 class="text-surface-700-200 h4">
                {$t("Available Tasks")}
              </h3>
            </div>
            <p class="text-surface-500-400 text-sm">
              {$t("Drag tasks to the selected panel or double-click to add")}
            </p>
          </div>

          <div class="space-y-2">
            <div class="flex items-center gap-3">
              <div
                class="from-primary-500 to-primary-600 h-1 w-8 rounded-full bg-gradient-to-r"
              ></div>
              <h3 class="text-surface-700-200 h4">
                {$t("Selected Tasks")}
              </h3>
            </div>
            <p class="text-surface-500-400 text-sm">
              {$t("Tasks will execute in the order shown below")}
            </p>
          </div>
        </div>

        <div class="contents md:contents">
          <div
            class="border-surface-200 bg-surface-50 dark:border-surface-700 dark:bg-surface-900/50 min-h-[300px] space-y-3 rounded-lg border p-4 transition-all duration-200"
          >
            {#if choices.length === 0}
              <div class="flex h-full items-center justify-center">
                <p class="text-surface-400-500 text-center text-sm">
                  {$t("No tasks available")}
                </p>
              </div>
            {:else}
              {#each choices as task}
                <div
                  class="group bg-surface-200 hover:bg-surface-300 dark:bg-surface-800 dark:hover:bg-surface-700 cursor-grab rounded-lg p-2 shadow-sm transition-all duration-200 hover:scale-[1.02] hover:shadow-md active:scale-95 active:cursor-grabbing"
                  draggable="true"
                  ondragstart={(e) => handleDragStart(e, task, false)}
                  ondblclick={() => addTask(task)}
                  role="button"
                  tabindex="0"
                  title="Double-click to add, or drag to position"
                >
                  <div class="flex items-center gap-3">
                    <div
                      class="bg-tertiary-500 group-hover:bg-tertiary-600 ml-3 h-2 w-2 rounded-full transition-all duration-200"
                    ></div>
                    <p
                      class="text-s text-surface-700 dark:text-surface-200 font-medium"
                    >
                      {$t(task)}
                    </p>
                  </div>
                </div>
              {/each}
            {/if}
          </div>

          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div
            class="border-primary-200 bg-primary-50 dark:border-primary-700 dark:bg-primary-900/20 min-h-[300px] space-y-3 rounded-lg border p-4 transition-all duration-200"
            ondragover={handleDragOver}
            ondrop={(e) => handleDrop(e)}
            ondragleave={handleDragLeave}
            ondragenter={() => (isOverContainer = true)}
          >
            {#if value.length === 0}
              <div class="flex h-full items-center justify-center">
                <div class="space-y-2 text-center">
                  <div
                    class="bg-primary-200 dark:bg-primary-800/50 mx-auto flex h-12 w-12 items-center justify-center rounded-full"
                  >
                    <div
                      class="border-primary-400 h-6 w-6 rounded-full border"
                    ></div>
                  </div>
                  <p class="text-surface-400-500 text-sm">
                    {$t("Drag tasks here to add them")}
                  </p>
                </div>
              </div>
            {:else}
              <!-- Above first item indicator -->
              {#if currentDragPosition === "above-first"}
                <div class="bg-primary-500 my-1 h-1 w-full rounded-full"></div>
              {/if}

              {#each value as taskItem, index}
                {#if dropIndicatorPos?.index === index && dropIndicatorPos?.position === "before" && currentDragPosition === "between"}
                  <div
                    class="bg-primary-500 my-1 h-1 w-full rounded-full"
                  ></div>
                {/if}

                <div
                  class="group bg-primary-100 hover:bg-primary-200 dark:bg-primary-800/50 dark:hover:bg-primary-700/50 relative cursor-grab rounded-lg p-2 shadow-sm transition-all duration-200 hover:scale-[1.02] hover:shadow-md active:scale-95 active:cursor-grabbing"
                  draggable="true"
                  ondragstart={(e) =>
                    handleDragStart(e, taskItem.name, true, index)}
                  ondragover={(e) => handleContainerDragOver(e, index)}
                  role="button"
                  tabindex="0"
                >
                  <div class="flex items-center justify-between gap-2">
                    <div class="flex flex-1 items-center gap-3">
                      <div
                        class="bg-primary-500 ml-3 flex h-5 w-5 shrink-0 items-center justify-center rounded-full font-mono text-xs font-bold text-white"
                      >
                        {index + 1}
                      </div>
                      <p
                        class="text-s text-surface-700 dark:text-surface-200 font-medium"
                      >
                        {$t(taskItem.name)}
                      </p>
                    </div>
                    <div
                      class="flex items-center gap-2"
                      role="none"
                      ondragstart={(e) => e.stopPropagation()}
                    >
                      <button
                        class="repeat-toggle shrink-0 rounded px-2 py-0.5 text-xs font-semibold transition-all duration-200"
                        class:repeat-on={taskItem.repeat}
                        class:repeat-off={!taskItem.repeat}
                        type="button"
                        title={taskItem.repeat
                          ? $t("Click to run once only")
                          : $t("Click to repeat")}
                        onclick={(e) => {
                          e.stopPropagation();
                          toggleRepeat(index);
                        }}
                      >
                        {taskItem.repeat ? $t("Repeat") : $t("Once")}
                      </button>
                      <button
                        class="variant-filled-error btn-icon opacity-0 transition-all duration-200 group-hover:opacity-100 hover:scale-110 active:scale-95"
                        type="button"
                        onclick={(e) => {
                          e.stopPropagation();
                          removeTask(index);
                        }}
                        title="Remove task"
                      >
                        <IconX size={16} />
                      </button>
                    </div>
                  </div>
                  <input type="hidden" value={taskItem.name} />
                </div>

                {#if dropIndicatorPos?.index === index && dropIndicatorPos?.position === "after" && currentDragPosition === "between"}
                  <div
                    class="bg-primary-500 my-1 h-1 w-full rounded-full"
                  ></div>
                {/if}
              {/each}

              <!-- Below last item indicator -->
              {#if currentDragPosition === "below-last"}
                <div class="bg-primary-500 my-1 h-1 w-full rounded-full"></div>
              {/if}
            {/if}
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .repeat-on {
    background-color: rgb(var(--color-primary-500) / 0.2);
    color: rgb(var(--color-primary-700));
    border: 1px solid rgb(var(--color-primary-400) / 0.5);
  }
  :global(.dark) .repeat-on {
    color: rgb(var(--color-primary-300));
    background-color: rgb(var(--color-primary-500) / 0.25);
  }
  .repeat-off {
    background-color: rgb(var(--color-surface-300) / 0.4);
    color: rgb(var(--color-surface-600));
    border: 1px solid rgb(var(--color-surface-400) / 0.4);
  }
  :global(.dark) .repeat-off {
    background-color: rgb(var(--color-surface-700) / 0.4);
    color: rgb(var(--color-surface-400));
  }
</style>
