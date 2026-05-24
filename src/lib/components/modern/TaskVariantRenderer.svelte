<script lang="ts">
  import { t } from "$lib/i18n/i18n";
  import type { MenuButton } from "$lib/menu/model";
  import { ui } from "$lib/stores.svelte";
  import TaskCard from "./TaskCard.svelte";

  interface Props {
    activeCategories: string[];
    categorizedButtons: Record<string, MenuButton[]>;
    disableActions: boolean;
  }

  let { activeCategories, categorizedButtons, disableActions }: Props =
    $props();

  let openAccordions = $state(new Set<string>());
  let seenCategories = new Set<string>();

  $effect(() => {
    // Only auto-open categories the first time we see them
    const newCats = activeCategories.filter((c) => !seenCategories.has(c));
    if (newCats.length > 0) {
      for (const c of newCats) {
        seenCategories.add(c);
        openAccordions.add(c);
      }
      openAccordions = new Set(openAccordions);
    }
  });

  function toggleAccordion(cat: string) {
    if (openAccordions.has(cat)) {
      openAccordions.delete(cat);
    } else {
      openAccordions.add(cat);
    }
    openAccordions = new Set(openAccordions);
  }
</script>

<div class="view-content">
  {#if ui.taskViewVariant === "cards"}
    <div class="cards-view">
      {#each activeCategories as cat}
        <section class="section">
          <div class="section-header">
            <div class="section-title">{$t(cat || "Other")}</div>
            <div class="section-line"></div>
            <div class="section-count">
              {String(categorizedButtons[cat].length).padStart(2, "0")}
            </div>
          </div>
          <div class="grid">
            {#each categorizedButtons[cat] as b}
              <TaskCard {b} {disableActions} variant="cards" />
            {/each}
          </div>
        </section>
      {/each}
    </div>
  {:else if ui.taskViewVariant === "palette"}
    <div class="palette-view">
      {#each activeCategories as cat}
        <div class="palette-section">
          <div class="palette-cat">{$t(cat || "Other")}</div>
          {#each categorizedButtons[cat] as b}
            <TaskCard {b} {disableActions} variant="palette" />
          {/each}
        </div>
      {/each}
    </div>
  {:else}
    <div class="accordion-view">
      {#each activeCategories as cat}
        {@const isOpen = openAccordions.has(cat)}
        <div class="accordion-item">
          <button
            class="accordion-trigger"
            onclick={() => toggleAccordion(cat)}
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
              width="14"
              height="14"
              class="chevron-toggle"
              style="transform: {isOpen ? 'rotate(90deg)' : 'rotate(0)'}"
              ><path d="m9 18 6-6-6-6" /></svg
            >
            <span class="acc-title">{$t(cat || "Other")}</span>
            <div class="spacer"></div>
            <span class="acc-count"
              >{String(categorizedButtons[cat].length).padStart(2, "0")}</span
            >
          </button>
          {#if isOpen}
            <div class="acc-content">
              <div class="grid">
                {#each categorizedButtons[cat] as b}
                  <TaskCard {b} {disableActions} variant="accordion" />
                {/each}
              </div>
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .view-content {
    flex: 1;
    overflow-y: auto;
    padding-bottom: 20px;
  }

  .section {
    padding: 0 20px;
    margin-bottom: 24px;
  }

  .section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
  }

  .section-title {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-3);
  }

  .section-line {
    height: 1px;
    flex: 1;
    background: var(--line-soft);
  }

  .section-count {
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-4);
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 10px;
  }

  /* Palette View */
  .palette-view {
    padding: 14px 20px;
  }

  .palette-section {
    background: var(--bg-1);
    border: 1px solid var(--line);
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 20px;
  }

  .palette-cat {
    padding: 8px 14px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-3);
    background: var(--bg-2);
    border-bottom: 1px solid var(--line);
  }

  /* Accordion View */
  .accordion-view {
    padding: 14px 20px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .accordion-item {
    background: var(--bg-1);
    border: 1px solid var(--line);
    border-radius: 12px;
    overflow: hidden;
  }

  .accordion-trigger {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    text-align: left;
    background: transparent;
    border: none;
    cursor: pointer;
  }

  .chevron-toggle {
    color: var(--text-3);
    transition: transform var(--dur-1);
  }

  .acc-title {
    font-weight: 600;
    font-size: 13.5px;
  }

  .acc-count {
    font-size: 11px;
    font-family: var(--font-mono);
    color: var(--text-4);
  }

  .acc-content {
    padding: 0 10px 10px;
  }

  .accordion-view .grid {
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  }

  .spacer {
    flex: 1;
  }
</style>
