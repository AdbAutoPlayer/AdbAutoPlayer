import { Events } from "@wailsio/runtime";
import { EventNames } from "$lib/log/eventNames";
import { reportError } from "$lib/utils/error-reporting";

export function logDebug(message: string) {
  emit({
    level: "DEBUG",
    message: message,
    timestamp: new Date().toISOString(),
  });
}

export function logInfo(message: string) {
  emit({
    level: "INFO",
    message: message,
    timestamp: new Date().toISOString(),
  });
}

export function logWarning(message: string) {
  emit({
    level: "WARNING",
    message: message,
    timestamp: new Date().toISOString(),
  });
}

export function logError(message: string) {
  emit({
    level: "ERROR",
    message: message,
    timestamp: new Date().toISOString(),
  });
}

function emit(message: LogMessage) {
  Events.Emit({
    name: EventNames.LOG_MESSAGE,
    data: message,
  }).catch((err) => {
    reportError(err);
  });
}
