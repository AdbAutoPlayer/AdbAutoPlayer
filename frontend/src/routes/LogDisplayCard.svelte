<script lang="ts">
  import { EventsOn } from "$lib/wailsjs/runtime";

  let logs: string[] = $state([]);

  const maxLogEntries = 1000;

  EventsOn("log-message", (logMessage: LogMessage) => {
    const urlRegex = /(https?:\/\/\S+)/g;

    let message: string = "";
    if (logMessage.level == "DEBUG") {
      const parts = [];
      if (logMessage.source_file) parts.push(`${logMessage.source_file}`);
      if (logMessage.function_name) parts.push(`${logMessage.function_name}`);
      if (logMessage.line_number) parts.push(`${logMessage.line_number}`);
      const debugInfo = parts.length > 0 ? ` (${parts.join("::")})` : "";

      message = `[${logMessage.level}]${debugInfo} ${logMessage.message.replace(
        urlRegex,
        '<a href="$1" target="_blank">$1</a>',
      )}`;
    } else {
      message = `[${logMessage.level}] ${logMessage.message.replace(
        urlRegex,
        '<a href="$1" target="_blank">$1</a>',
      )}`;
    }

    if (logs.length >= maxLogEntries) {
      logs.shift();
    }
    logs.push(message);
  });

  let logContainer: HTMLDivElement;

  function getLogColor(message: string): string {
    if (message.includes("[DEBUG]")) return "cyan";
    if (message.includes("[INFO]")) return "green";
    if (message.includes("[WARNING]")) return "yellow";
    if (message.includes("[ERROR]")) return "red";
    if (message.includes("[FATAL]")) return "darkred";
    return "white";
  }

  $effect(() => {
    if (logContainer && logs.length > 0) {
      requestAnimationFrame(() => {
        logContainer.scrollTop = logContainer.scrollHeight;
      });
    }
  });
</script>

<div class="flex-grow min-h-[200px] p-4 flex flex-col">
  <div class="card p-4 bg-surface-100-900/50 flex-grow h-full flex-col">
    <div
      class="select-text font-mono h-full overflow-y-scroll break-words whitespace-normal flex-grow"
      bind:this={logContainer}
    >
      {#each logs as message}
        <div style="color: {getLogColor(message)}">
          {@html message}
        </div>
      {/each}
    </div>
  </div>
</div>
