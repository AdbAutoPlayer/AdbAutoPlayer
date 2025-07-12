import { capitalizeError } from "$lib/utils/string";
import { toaster } from "$lib/toast/toaster-svelte";
import { logError } from "$lib/log/log-events";
import { reportError } from "$lib/utils/error-reporting";

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

  reportError(error);
  if (logToLogDisplay) logError(message); // Display in LogDisplay in case the toast disappears too fast

  // User feedback
  toaster.error({
    title,
    description: message,
  });
}
