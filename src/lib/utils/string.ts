/**
 * Capitalizes the first letter of a string.
 * @param str - The input string (or null/undefined).
 * @returns The capitalized string, or an empty string if input is falsy.
 *
 * @example
 * capitalize('hello')      // 'Hello'
 * capitalize('')           // ''
 * capitalize(null)         // ''
 * capitalize(undefined)    // ''
 */
export function capitalize(str: string | null | undefined): string {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Safely capitalizes an error (or any value) after converting to string.
 * @example
 * capitalizeError(new Error('fail')) // 'Error: Fail'
 * capitalizeError(null)              // ''
 */
export function capitalizeError(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error);
  return capitalize(message || "");
}
