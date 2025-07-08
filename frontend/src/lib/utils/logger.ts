import { Events } from "@wailsio/runtime";
import { EventNames } from "$lib/eventNames";

export function LogDebug(message: string) {
  emit({
    level: "DEBUG",
    message: message,
    timestamp: new Date().toISOString(),
  });
}

export function LogInfo(message: string) {
  emit({
    level: "INFO",
    message: message,
    timestamp: new Date().toISOString(),
  });
}

export function LogWarning(message: string) {
  emit({
    level: "WARNING",
    message: message,
    timestamp: new Date().toISOString(),
  });
}

export function LogError(message: string) {
  emit({
    level: "ERROR",
    message: message,
    timestamp: new Date().toISOString(),
  });
}

export function LogFatal(message: string) {
  emit({
    level: "FATAL",
    message: message,
    timestamp: new Date().toISOString(),
  });
}

function emit(message: LogMessage) {
  Events.Emit({
    name: EventNames.LOG_MESSAGE,
    data: message,
  }).catch((err) => console.error("Background emit failed:", err));
}
