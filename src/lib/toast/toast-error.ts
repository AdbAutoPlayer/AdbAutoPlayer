import { capitalizeError } from "#lib/utils/string.ts";
import { toaster } from "#lib/toast/toaster-svelte.ts";
import { logError } from "#lib/log/log-events.ts";
import { reportError } from "#lib/utils/error-reporting.ts";

type ErrorToastOptions = {
  title?: string;
  logToLogDisplay?: boolean;
  profile?: number;
};

/**
 * Handles errors consistently: logs to console/server + shows a toast.
 * @example
 * showErrorToast(new Error('Update failed'), {
 *   title: 'Failed to Check for Updates'
 * });
 */
export async function showErrorToast(
  error: unknown | string,
  options: ErrorToastOptions = {},
) {
  const {
    title = "Something went wrong",
    logToLogDisplay = true,
    profile = undefined,
  } = options;

  const message = capitalizeError(error);

  reportError(error);
  if (logToLogDisplay) {
    await logError(message, profile); // Display in LogDisplay in case the toast disappears too fast
  }
  console.error(error);

  toaster.error({
    title,
    description: message,
  });
}
