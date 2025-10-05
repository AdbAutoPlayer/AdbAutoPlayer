<script lang="ts">
  import IconX from "$lib/components/icons/feather/IconX.svelte";
  import IconArrowDown from "$lib/components/icons/feather/IconArrowDown.svelte";
  import IconArrowUp from "$lib/components/icons/feather/IconArrowUp.svelte";
  import type { TextDisplayCardItem } from "$lib/log/logHelper";

  type TextDisplayCardProps = {
    entries?: TextDisplayCardItem[];
    maxEntries?: number;
    enableSearch?: boolean;
  };

  let {
    entries = $bindable([]),
    maxEntries = 1000,
    enableSearch = true,
  }: TextDisplayCardProps = $props();

  let searchTerm: string = $state("");
  let searchVisible: boolean = $state(false);
  let currentMatchIndex: number = $state(-1);
  let searchInput: HTMLInputElement | null = $state(null);
  let logContainer: HTMLDivElement;

  // Public API methods
  export function appendEntry(entry: TextDisplayCardItem) {
    insertEntry(entry);
    if (entries.length > maxEntries) {
      entries.shift();
    }
  }

  export function slice(start: number, end?: number) {
    entries = entries.slice(start, end);
  }

  export function clear() {
    entries = [];
  }

  function insertEntry(entry: TextDisplayCardItem) {
    let i = entries.length - 1;
    while (i >= 0 && entries[i].timestamp.isAfter(entry.timestamp)) {
      i--;
    }
    entries.splice(i + 1, 0, entry);
  }

  function highlightText(
    text: string,
    searchTerm: string,
    logIndex: number,
  ): string {
    if (!searchTerm) return text;

    const regex = new RegExp(
      `(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`,
      "gi",
    );

    let matchCounter = 0;
    let cumulativeMatchIndex = 0;

    for (let i = 0; i < logIndex; i++) {
      const matches = entries[i].message.match(regex);
      if (matches) {
        cumulativeMatchIndex += matches.length;
      }
    }

    return text.replace(regex, (match) => {
      const isCurrentMatch =
        cumulativeMatchIndex + matchCounter === currentMatchIndex;
      matchCounter++;

      if (isCurrentMatch) {
        return `<mark class="bg-primary-400 text-primary-900 ring-2 ring-primary-600">${match}</mark>`;
      } else {
        return `<mark class="bg-warning-200 text-warning-900">${match}</mark>`;
      }
    });
  }

  const totalMatchCount = $derived.by(() => {
    if (!searchTerm) return 0;

    let total = 0;
    const regex = new RegExp(
      `(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`,
      "gi",
    );

    entries.forEach((entry) => {
      const matches = entry.message.match(regex);
      if (matches) {
        total += matches.length;
      }
    });

    return total;
  });

  function toggleSearch() {
    searchVisible = !searchVisible;
    if (searchVisible) {
      setTimeout(() => searchInput?.focus(), 100);
    } else {
      searchTerm = "";
      currentMatchIndex = -1;
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (!enableSearch) return;

    if (event.ctrlKey && event.key === "f") {
      event.preventDefault();
      toggleSearch();
    }

    if (event.key === "Escape" && searchVisible) {
      toggleSearch();
    }

    if (event.key === "Enter" && searchVisible && totalMatchCount > 0) {
      event.preventDefault();
      if (event.shiftKey) {
        currentMatchIndex =
          currentMatchIndex <= 0 ? totalMatchCount - 1 : currentMatchIndex - 1;
      } else {
        currentMatchIndex =
          currentMatchIndex >= totalMatchCount - 1 ? 0 : currentMatchIndex + 1;
      }
      scrollToMatch();
    }
  }

  function scrollToMatch() {
    if (currentMatchIndex >= 0 && currentMatchIndex < totalMatchCount) {
      const matchElements = logContainer.querySelectorAll("mark");
      if (matchElements[currentMatchIndex]) {
        matchElements[currentMatchIndex].scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      }
    }
  }

  function clearSearch() {
    searchTerm = "";
    currentMatchIndex = -1;
  }

  $effect(() => {
    if (logContainer && entries.length > 0 && !searchTerm) {
      logContainer.scrollTop = logContainer.scrollHeight;
    }
  });

  $effect(() => {
    if (searchTerm && currentMatchIndex >= totalMatchCount) {
      currentMatchIndex = totalMatchCount > 0 ? 0 : -1;
    }
  });

  $effect(() => {
    if (searchTerm && currentMatchIndex >= 0 && totalMatchCount > 0) {
      setTimeout(() => scrollToMatch(), 50);
    }
  });
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="flex min-h-6 flex-grow flex-col pr-4 pb-4 pl-4">
  <div
    class="relative h-full flex-grow flex-col card bg-surface-100-900/50 p-4"
  >
    {#if enableSearch && searchVisible}
      <div
        class="absolute top-2 right-2 z-10 flex items-center gap-2 rounded-lg border border-surface-300-700 bg-surface-200-800 p-2 shadow-lg"
      >
        <input
          bind:this={searchInput}
          bind:value={searchTerm}
          placeholder="Search..."
          class="w-48 border-none bg-transparent text-sm text-surface-900-100 outline-none"
          oninput={() => (currentMatchIndex = searchTerm ? 0 : -1)}
        />

        {#if searchTerm}
          <div class="no-select text-xs whitespace-nowrap text-surface-600-400">
            {totalMatchCount > 0
              ? `${currentMatchIndex + 1}/${totalMatchCount}`
              : "0/0"}
          </div>

          <button
            class="hover:bg-surface-300-600 no-select rounded px-2 py-1 text-xs"
            disabled={totalMatchCount === 0}
            onclick={() => {
              currentMatchIndex =
                currentMatchIndex <= 0
                  ? totalMatchCount - 1
                  : currentMatchIndex - 1;
              scrollToMatch();
            }}
          >
            <IconArrowUp size={14} strokeWidth={2} />
          </button>
          <button
            class="hover:bg-surface-300-600 no-select rounded px-2 py-1 text-xs"
            disabled={totalMatchCount === 0}
            onclick={() => {
              currentMatchIndex =
                currentMatchIndex >= totalMatchCount - 1
                  ? 0
                  : currentMatchIndex + 1;
              scrollToMatch();
            }}
          >
            <IconArrowDown size={14} strokeWidth={2} />
          </button>

          <button
            class="hover:bg-surface-300-600 no-select rounded px-2 py-1"
            onclick={clearSearch}
          >
            <IconX size={14} strokeWidth={2} />
          </button>
        {/if}

        <button
          class="hover:bg-surface-300-600 no-select rounded px-2 py-1 text-xs"
          onclick={toggleSearch}
        >
          Close
        </button>
      </div>
    {/if}

    <div
      class="h-full flex-grow overflow-y-scroll font-mono break-words whitespace-normal select-text"
      bind:this={logContainer}
    >
      {#each entries as { message, html_class }, index}
        <div class={html_class}>
          {@html searchTerm
            ? highlightText(message, searchTerm, index)
            : message}
        </div>
      {/each}
    </div>
  </div>
</div>
