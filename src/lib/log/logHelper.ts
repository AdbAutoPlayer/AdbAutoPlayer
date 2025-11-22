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

function sanitizeMessage(message: string): string {
  // Regex to match Windows user-profile path:
  // C:\Users\anything_until_next_backslash\
  const userPathRegex = /C:\\Users\\[^\\]+\\/gi;

  return message.replace(userPathRegex, "C:\\Users\\$env:USERNAME\\");
}

export function logMessageToTextDisplayCardItem(
  logMessage: LogMessage,
): TextDisplayCardItem {
  const sanitized = sanitizeMessage(logMessage.message);
  const formatted = formatMessage(sanitized);
  const message = `[${logMessage.level}] ${formatted}`;

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
