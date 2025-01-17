<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    title,
    children,
  }: {
    title: string;
    children: Snippet;
  } = $props();
</script>

<div class="command-panel">
  <h2>{title}</h2>
  {@render children?.()}
</div>

<style>
  .command-panel {
    margin-bottom: 2rem;
    padding-bottom: 1rem;
    padding-left: 1rem;
    padding-right: 1rem;
    margin-left: 1.5rem;
    margin-right: 1.5rem;
    border: 2px solid rgba(25, 25, 25, 0.8);
    background-color: rgba(31, 31, 31, 0.8);
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    justify-content: center;
    text-align: center;
  }
</style>
