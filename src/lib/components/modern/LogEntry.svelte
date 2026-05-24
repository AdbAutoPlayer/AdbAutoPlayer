<script lang="ts">
  import type { TextDisplayCardItem } from "$lib/log/logHelper";
  import { Instant } from "@js-joda/core";

  interface Props {
    entry: TextDisplayCardItem;
  }

  let { entry }: Props = $props();

  function fmtTime(instant: Instant) {
    const d = new Date(instant.toEpochMilli());
    return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}:${String(d.getSeconds()).padStart(2, "0")}`;
  }
</script>

<div class="log-line">
  <span class="time">{fmtTime(entry.timestamp)}</span>
  <span class="level-tag" data-level={(entry as any).level || "INFO"}>
    {(entry as any).level || "INFO"}
  </span>
  <span class="message">
    {@html entry.message.replace(/^\[[A-Z]+\]\s*/, "")}
  </span>
</div>

<style>
  .log-line {
    display: grid;
    grid-template-columns: 74px 62px 1fr;
    gap: 8px;
    padding: 2px 14px;
    min-width: 0;
  }

  .time {
    color: var(--text-4);
  }

  .level-tag {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    border: 1px solid;
    border-radius: 4px;
    padding: 1px 0;
    text-align: center;
    height: fit-content;
  }

  .level-tag[data-level="DEBUG"] {
    color: var(--text-4);
    border-color: var(--text-4);
  }
  .level-tag[data-level="INFO"] {
    color: var(--accent-hi);
    border-color: color-mix(in oklab, var(--accent-hi) 40%, transparent);
  }
  .level-tag[data-level="WARNING"] {
    color: var(--warn);
    border-color: color-mix(in oklab, var(--warn) 45%, transparent);
  }
  .level-tag[data-level="ERROR"] {
    color: var(--err);
    border-color: color-mix(in oklab, var(--err) 45%, transparent);
  }
  .level-tag[data-level="FATAL"] {
    color: var(--err);
    border-color: var(--err);
    font-weight: 700;
  }

  .message {
    text-wrap: pretty;
    word-break: break-word;
    white-space: pre-wrap;
    min-width: 0;
  }

  /* Compact Mode adjustments inside layout components if inherited */
  :global(.log-panel.compact[data-position="bottom"]) .log-line {
    grid-template-columns: 68px 58px 1fr;
    padding: 1px 14px;
  }
</style>
