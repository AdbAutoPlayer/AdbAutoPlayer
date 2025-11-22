import posthog, { type Properties } from "posthog-js";

/**
 * Reports errors appropriately based on environment:
 * - Development (version 0.0.0): logs to console
 * - Production: sends to PostHog for tracking
 */
export function reportError(error: unknown, additionalProperties?: Properties) {
  if (!error) {
    return;
  }

  try {
    posthog.captureException(error, additionalProperties);
  } catch (e) {
    console.error(e);
  }
}
