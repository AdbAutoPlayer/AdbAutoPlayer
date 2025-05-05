<script lang="ts">
  let {
    constraint,
    value,
    name,
  }: {
    constraint: MyCustomRoutineConstraint;
    value: string[];
    name: string;
  } = $props();

  let selectedTask = $state("");

  function addTask() {
    if (!selectedTask) return;
    value = [...value, selectedTask];
    selectedTask = "";
  }

  function removeTask(index: number) {
    value = value.filter((_, i) => i !== index);
  }

  function clearList() {
    if (confirm("Are you sure you want to clear all tasks?")) {
      value = [];
    }
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
          <!-- Added flex and gap-4 to align items side by side -->
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

      <div class="action-list mt-2 flex flex-col gap-3">
        {#if value.length === 0}
          <p>No actions added</p>
        {:else}
          {#each value as task, index}
            <div class="action-item flex items-center justify-between gap-2">
              <div class="text-left"><p>{task}</p></div>
              <button
                class="badge-icon preset-filled-error-100-900 hover:preset-filled-error-500"
                type="button"
                onclick={() => removeTask(index)}
              >
                <span class="h3">×</span>
              </button>
              <input type="hidden" {name} value={task} />
            </div>
          {/each}
        {/if}
      </div>

      <div class="mt-2 flex items-center gap-2">
        <select class="select" bind:value={selectedTask}>
          <option value="">Select an action to add...</option>
          {#each constraint.choices as choice}
            <option value={choice}>{choice}</option>
          {/each}
        </select>
        <button
          type="button"
          class="btn preset-filled-secondary-100-900 hover:preset-filled-secondary-500"
          onclick={addTask}>Add Action</button
        >
      </div>
    </div>
  {:else}
    <p>No options available</p>
  {/if}
</div>
