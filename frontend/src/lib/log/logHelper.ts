import { Instant } from "@js-joda/core";

export function formatMessage(message: string): string {
  const urlRegex = /(https?:\/\/[^\s'"]+)/g;
  return message
    .replace(urlRegex, '<a class="anchor" href="$1" target="_blank">$1</a>')
    .replace(/\r?\n/g, "<br>");
}

export function getLogClass(message: string): string {
  if (message.includes("[DEBUG]")) return "text-primary-500";
  if (message.includes("[INFO]")) return "text-success-500";
  if (message.includes("[WARNING]")) return "text-warning-500";
  if (message.includes("[ERROR]")) return "text-error-500";
  if (message.includes("[FATAL]")) return "text-error-950";
  return "text-primary-50";
}

export function logMessageToTextDisplayCardItem(
  logMessage: LogMessage,
  alwaysDisplayDebugInfo: boolean = false,
): TextDisplayCardItem {
  let message: string;
  if (logMessage.level === "DEBUG" || alwaysDisplayDebugInfo) {
    const parts = [];
    if (logMessage.source_file) parts.push(logMessage.source_file);
    if (logMessage.function_name) parts.push(logMessage.function_name);
    if (logMessage.line_number) parts.push(String(logMessage.line_number));
    const debugInfo = parts.length > 0 ? ` (${parts.join("::")})` : "";

    message = `[${logMessage.level}]${debugInfo} ${formatMessage(logMessage.message)}`;
  } else {
    message = `[${logMessage.level}] ${formatMessage(logMessage.message)}`;
  }

  return {
    message,
    timestamp: Instant.parse(logMessage.timestamp),
    html_class: logMessage.html_class ?? getLogClass(message),
  };
}

export type TextDisplayCardItem = {
  message: string;
  timestamp: Instant;
  html_class: string;
};
