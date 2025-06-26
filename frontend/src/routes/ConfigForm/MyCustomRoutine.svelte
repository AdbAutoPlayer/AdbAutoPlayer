<script lang="ts">
  import IconX from "../Icons/Feather/IconX.svelte";

  let {
    constraint,
    value = $bindable(),
    name,
  }: {
    constraint: MyCustomRoutineConstraint;
    value: string[];
    name: string;
  } = $props();

  let draggedItem = $state<string | null>(null);
  let draggedFromSelected = $state(false);
  let draggedIndex = $state(-1);

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
    }
  }

  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = draggedFromSelected ? "move" : "copy";
    }
  }

  function handleDrop(e: DragEvent, targetIndex?: number) {
    e.preventDefault();
    if (!draggedItem) return;

    if (draggedFromSelected) {
      // Moving within selected tasks
      if (targetIndex !== undefined && draggedIndex !== -1) {
        const newValue = [...value];
        const [movedItem] = newValue.splice(draggedIndex, 1);
        newValue.splice(targetIndex, 0, movedItem);
        value = newValue;
      }
    } else {
      // Adding from available tasks
      if (targetIndex !== undefined) {
        // Insert at specific position
        const newValue = [...value];
        newValue.splice(targetIndex, 0, draggedItem);
        value = newValue;
      } else {
        // Add to end
        value = [...value, draggedItem];
      }
    }

    draggedItem = null;
    draggedFromSelected = false;
    draggedIndex = -1;
  }

  function handleDropOnSelected(e: DragEvent, targetIndex: number) {
    e.preventDefault();
    e.stopPropagation();
    handleDrop(e, targetIndex);
  }

  function removeTask(index: number) {
    value = value.filter((_, i) => i !== index);
  }

  function clearList() {
    if (confirm("Are you sure you want to clear all tasks?")) {
      value = [];
    }
  }

  function addTask(task: string) {
    value = [...value, task];
  }

  let taskHeader = $state("Tasks");
  let taskBracketInfo = $state("");
  let taskDescription = $state(
    "These actions will run in the order shown below.",
  );

  const lowerName = name.toLowerCase();

  if (lowerName.includes("daily")) {
    taskHeader = "Daily Tasks";
    taskBracketInfo = "(Run once per day)";
    taskDescription = "These actions will run once at the start of each day.";
  } else if (lowerName.includes("repeat")) {
    taskHeader = "Repeating Tasks";
    taskBracketInfo = "(Run continuously)";
    taskDescription =
      "These actions will run repeatedly in order, over and over again.";
  }
</script>

<div class="mx-auto flex w-full flex-col gap-4 p-4">
  {#if constraint.choices.length > 0}
    <div>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-4">
          <h6 class="h6">{taskHeader}</h6>
          <span class="">{taskBracketInfo}</span>
        </div>
        <button
          class="btn preset-filled-warning-100-900 hover:preset-filled-warning-500"
          type="button"
          onclick={clearList}>Clear List</button
        >
      </div>
      <p>{taskDescription}</p>

      <div class="mt-4 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <!-- Available Tasks Panel -->
        <div class="flex flex-col">
          <h6 class="text-surface-600-300 mb-3 text-sm font-semibold">
            Available Actions (Drag or double-click to add)
          </h6>
          <div
            class="border-surface-300-600 bg-surface-50-900 flex min-h-[200px] flex-col gap-2 rounded-lg border-2 border-dashed p-3"
          >
            {#if constraint.choices.length === 0}
              <p class="text-surface-400-500 text-center text-sm">
                No actions available
              </p>
            {:else}
              {#each constraint.choices as task}
                <div
                  class="bg-surface-100-800 cursor-grab rounded-md p-3 shadow-sm transition-all hover:shadow-md active:cursor-grabbing"
                  draggable="true"
                  ondragstart={(e) => handleDragStart(e, task, false)}
                  ondblclick={() => addTask(task)}
                  role="button"
                  tabindex="0"
                  title="Double-click to add, or drag to position"
                >
                  <p class="text-sm">{task}</p>
                </div>
              {/each}
            {/if}
          </div>
        </div>

        <!-- Selected Tasks Panel -->
        <div class="flex flex-col">
          <h6 class="text-surface-600-300 mb-3 text-sm font-semibold">
            Selected Actions (Drag to reorder)
          </h6>
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div
            class="border-primary-300-600 bg-primary-50-900/20 flex min-h-[200px] flex-col gap-2 rounded-lg border-2 border-dashed p-3"
            ondragover={handleDragOver}
            ondrop={(e) => handleDrop(e)}
          >
            {#if value.length === 0}
              <p class="text-surface-400-500 text-center text-sm">
                Drag actions here to add them
              </p>
            {:else}
              {#each value as task, index}
                <div
                  class="group bg-primary-100-800 relative cursor-grab rounded-md p-3 shadow-sm transition-all hover:shadow-md active:cursor-grabbing"
                  draggable="true"
                  ondragstart={(e) => handleDragStart(e, task, true, index)}
                  ondragover={handleDragOver}
                  ondrop={(e) => handleDropOnSelected(e, index)}
                  role="button"
                  tabindex="0"
                >
                  <div class="flex items-center justify-between gap-2">
                    <div class="flex items-center gap-2">
                      <span class="text-surface-500-400 text-xs font-medium">
                        {index + 1}.
                      </span>
                      <p class="text-sm">{task}</p>
                    </div>
                    <button
                      class="badge-icon preset-filled-error-100-900 opacity-0 transition-opacity group-hover:opacity-100 hover:preset-filled-error-500"
                      type="button"
                      onclick={() => removeTask(index)}
                    >
                      <IconX size={16} />
                    </button>
                  </div>
                  <input type="hidden" {name} value={task} />
                </div>
              {/each}
            {/if}
          </div>
        </div>
      </div>
    </div>
  {:else}
    <p>No options available</p>
  {/if}
</div>
