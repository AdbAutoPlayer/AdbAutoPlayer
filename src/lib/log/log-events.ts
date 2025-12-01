import { EventNames } from "$lib/log/eventNames";
import { emit } from "@tauri-apps/api/event";

export async function logDebug(message: string) {
  await emitLogMessageEvent({
    level: "DEBUG",
    message: message,
    timestamp: new Date().toISOString(),
  });
}

export async function logInfo(message: string) {
  await emitLogMessageEvent({
    level: "INFO",
    message: message,
    timestamp: new Date().toISOString(),
  });
}

export async function logWarning(message: string) {
  await emitLogMessageEvent({
    level: "WARNING",
    message: message,
    timestamp: new Date().toISOString(),
  });
}

export async function logError(message: string, profile?: number) {
  await emitLogMessageEvent({
    level: "ERROR",
    message: message,
    timestamp: new Date().toISOString(),
    profile_index: profile,
  });
}

async function emitLogMessageEvent(message: LogMessage) {
  await emit<LogMessage>(EventNames.LOG_MESSAGE, message);
}
