import { capitalizeError } from "$lib/utils/string";
import { toaster } from "$lib/utils/toaster-svelte";
import { LogError } from "$lib/utils/logger";

type ErrorToastOptions = {
  title?: string;
  logToLogDisplay?: boolean;
};

/**
 * Handles errors consistently: logs to console/server + shows a toast.
 * @example
 * showErrorToast(new Error('Update failed'), {
 *   title: 'Failed to Check for Updates'
 * });
 */
export function showErrorToast(
  error: unknown,
  options: ErrorToastOptions = {},
) {
  const { title = "Something went wrong", logToLogDisplay = true } = options;

  const message = capitalizeError(error);

  // Logging
  console.error(error); // Original error for debugging
  if (logToLogDisplay) LogError(message); // Display in LogDisplay in case the toast disappears too fast

  // User feedback
  toaster.error({
    title,
    description: message,
  });
}
