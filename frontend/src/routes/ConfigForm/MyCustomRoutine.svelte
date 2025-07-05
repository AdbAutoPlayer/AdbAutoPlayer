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

<div class="mx-auto flex w-full max-w-6xl flex-col gap-8 p-6">
  {#if constraint.choices.length > 0}
    <div class="space-y-6">
      <!-- Header Section -->
      <div
        class="flex items-center justify-between rounded-xl bg-gradient-to-r from-primary-50 to-secondary-50 p-4 shadow-lg dark:from-primary-900/20 dark:to-secondary-900/20"
      >
        <div class="space-y-2">
          <div class="flex items-center gap-4">
            <h2 class="h2 text-surface-800 dark:text-surface-100">
              {taskHeader}
            </h2>
            <span class="variant-soft-secondary badge font-medium">
              {taskBracketInfo}
            </span>
          </div>
          <p class="text-surface-600-300 max-w-2xl text-sm leading-relaxed">
            {taskDescription}
          </p>
        </div>
        <button
          class="btn rounded-lg bg-red-800 px-4 py-2 font-medium text-red-100 shadow-md transition-all duration-200 hover:scale-105 hover:bg-red-600 hover:text-white hover:shadow-lg"
          type="button"
          onclick={clearList}
        >
          Clear List
        </button>
      </div>

      <!-- Main Content Grid -->
      <div class="grid grid-cols-1 gap-x-8 gap-y-4 lg:grid-cols-2">
        <!-- Headers Row -->
        <div class="contents lg:contents">
          <!-- Available Tasks Header -->
          <div class="space-y-2">
            <div class="flex items-center gap-3">
              <div
                class="h-1 w-8 rounded-full bg-gradient-to-r from-tertiary-500 to-tertiary-600"
              ></div>
              <h3 class="text-surface-700-200 h4">Available Actions</h3>
            </div>
            <p class="text-surface-500-400 text-sm">
              Drag actions to the selected panel or double-click to add
            </p>
          </div>

          <!-- Selected Tasks Header -->
          <div class="space-y-2">
            <div class="flex items-center gap-3">
              <div
                class="h-1 w-8 rounded-full bg-gradient-to-r from-primary-500 to-primary-600"
              ></div>
              <h3 class="text-surface-700-200 h4">Selected Actions</h3>
              {#if value.length > 0}
                <span class="variant-filled-primary badge text-xs">
                  {value.length}
                  {value.length === 1 ? "task" : "tasks"}
                </span>
              {/if}
            </div>
            <p class="text-surface-500-400 text-sm">
              Actions will execute in the order shown below
            </p>
          </div>
        </div>

        <!-- Boxes Row -->
        <div class="contents lg:contents">
          <!-- Available Tasks Box -->
          <div
            class="min-h-[300px] space-y-3 rounded-lg border border-surface-200 bg-surface-50 p-4 transition-all duration-200 dark:border-surface-700 dark:bg-surface-900/50"
          >
            {#if constraint.choices.length === 0}
              <div class="flex h-full items-center justify-center">
                <p class="text-surface-400-500 text-center text-sm">
                  No actions available
                </p>
              </div>
            {:else}
              {#each constraint.choices as task}
                <div
                  class="group cursor-grab rounded-lg bg-surface-200 p-2 shadow-sm transition-all duration-200 hover:scale-[1.02] hover:bg-surface-300 hover:shadow-md active:scale-95 active:cursor-grabbing dark:bg-surface-800 dark:hover:bg-surface-700"
                  draggable="true"
                  ondragstart={(e) => handleDragStart(e, task, false)}
                  ondblclick={() => addTask(task)}
                  role="button"
                  tabindex="0"
                  title="Double-click to add, or drag to position"
                >
                  <div class="flex items-center gap-3">
                    <div
                      class="h-2 w-2 rounded-full bg-tertiary-500 transition-all duration-200 group-hover:bg-tertiary-600"
                    ></div>
                    <p
                      class="text-s font-medium text-surface-700 dark:text-surface-200"
                    >
                      {task}
                    </p>
                  </div>
                </div>
              {/each}
            {/if}
          </div>

          <!-- Selected Tasks Box -->
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div
            class="min-h-[300px] space-y-3 rounded-lg border border-primary-200 bg-primary-50 p-4 transition-all duration-200 dark:border-primary-700 dark:bg-primary-900/20"
            ondragover={handleDragOver}
            ondrop={(e) => handleDrop(e)}
          >
            {#if value.length === 0}
              <div class="flex h-full items-center justify-center">
                <div class="space-y-2 text-center">
                  <div
                    class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary-200 dark:bg-primary-800/50"
                  >
                    <div
                      class="h-6 w-6 rounded-full border border-primary-400"
                    ></div>
                  </div>
                  <p class="text-surface-400-500 text-sm">
                    Drag actions here to add them
                  </p>
                </div>
              </div>
            {:else}
              {#each value as task, index}
                <div
                  class="group relative cursor-grab rounded-lg bg-primary-100 p-2 shadow-sm transition-all duration-200 hover:scale-[1.02] hover:bg-primary-200 hover:shadow-md active:scale-95 active:cursor-grabbing dark:bg-primary-800/50 dark:hover:bg-primary-700/50"
                  draggable="true"
                  ondragstart={(e) => handleDragStart(e, task, true, index)}
                  ondragover={handleDragOver}
                  ondrop={(e) => handleDropOnSelected(e, index)}
                  role="button"
                  tabindex="0"
                >
                  <div class="flex items-center justify-between gap-2">
                    <div class="flex flex-1 items-center gap-3">
                      <div
                        class="flex h-5 w-5 items-center justify-center rounded-full bg-primary-500 font-mono text-xs font-bold text-white"
                      >
                        {index + 1}
                      </div>
                      <p
                        class="text-s font-medium text-surface-700 dark:text-surface-200"
                      >
                        {task}
                      </p>
                    </div>
                    <button
                      class="variant-filled-error absolute top-1/2 right-2 btn-icon -translate-y-1/2 opacity-0 transition-all duration-200 group-hover:opacity-100 hover:scale-110 active:scale-95"
                      type="button"
                      onclick={() => removeTask(index)}
                      title="Remove task"
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
    <div class="variant-ghost-warning card p-8 text-center">
      <div
        class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-warning-100 dark:bg-warning-900/30"
      >
        <div class="h-8 w-8 rounded-full bg-warning-500"></div>
      </div>
      <p class="text-surface-600-300 text-lg">No options available</p>
    </div>
  {/if}
</div>
