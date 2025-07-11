import posthog, { type Properties } from "posthog-js";
import { version } from "$app/environment";

/**
 * Reports errors appropriately based on environment:
 * - Development (version 0.0.0): logs to console
 * - Production: sends to PostHog for tracking
 */
export function reportError(error: unknown, additionalProperties?: Properties) {
  if (isDev()) {
    console.error(error, additionalProperties);
    return;
  }

  try {
    posthog.captureException(error, additionalProperties);
  } catch (e) {
    // can be ignored because console is not available in webview
    return;
  }
}

export function logDevOnly(error: unknown) {
  if (isDev()) {
    console.error(error);
    return;
  }
}

function isDev() {
  // "0.0.0" is used to identify development environment
  return "0.0.0" === version;
}
