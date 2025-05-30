<script lang="ts">
  import { EventsOn } from "$lib/wailsjs/runtime";

  let logs: string[] = $state([]);

  const maxLogEntries = 1000;

  function formatMessage(message: string): string {
    const urlRegex = /(https?:\/\/[^\s'"]+)/g;
    return message.replace(
      urlRegex,
      '<a class="anchor" href="$1" target="_blank">$1</a>',
    );
  }

  EventsOn("log-message", (logMessage: LogMessage) => {
    let message: string = "";
    if (logMessage.level == "DEBUG") {
      const parts = [];
      if (logMessage.source_file) parts.push(`${logMessage.source_file}`);
      if (logMessage.function_name) parts.push(`${logMessage.function_name}`);
      if (logMessage.line_number) parts.push(`${logMessage.line_number}`);
      const debugInfo = parts.length > 0 ? ` (${parts.join("::")})` : "";

      message = `[${logMessage.level}]${debugInfo} ${formatMessage(logMessage.message)}`;
    } else {
      message = `[${logMessage.level}] ${formatMessage(logMessage.message)}`;
    }

    if (logs.length >= maxLogEntries) {
      logs.shift();
    }
    logs.push(message);
  });

  // keeps the app version in the log
  EventsOn("log-clear", () => {
    logs = logs.slice(0, 2);
  });

  let logContainer: HTMLDivElement;

  function getLogColor(message: string): string {
    if (message.includes("[DEBUG]")) return "text-primary-500";
    if (message.includes("[INFO]")) return "text-success-500";
    if (message.includes("[WARNING]")) return "text-warning-500";
    if (message.includes("[ERROR]")) return "text-error-500";
    if (message.includes("[FATAL]")) return "text-error-950";
    return "text-primary-50";
  }

  // sometimes LLMs will suggest using $effect.pre() always ignore it because it's wrong
  $effect(() => {
    if (logContainer && logs.length > 0) {
      logContainer.scrollTop = logContainer.scrollHeight;
    }
  });
</script>

<div class="flex min-h-6 flex-grow flex-col p-4">
  <div class="h-full flex-grow flex-col card bg-surface-100-900/50 p-4">
    <div
      class="h-full flex-grow overflow-y-scroll font-mono break-words whitespace-normal select-text"
      bind:this={logContainer}
    >
      {#each logs as message}
        <div class={getLogColor(message)}>
          {@html message}
        </div>
      {/each}
    </div>
  </div>
</div>
