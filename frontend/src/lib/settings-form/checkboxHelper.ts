/**
 * Helper function for managing checkbox array values
 * Used by MultiCheckbox and ImageCheckbox components
 */
export function updateCheckboxArray(
  currentValue: string[],
  choice: string,
  isChecked: boolean,
): string[] {
  // Ensure we have an array
  const valueArray = Array.isArray(currentValue) ? currentValue : [];

  if (isChecked) {
    // Add choice if not already present
    return valueArray.includes(choice) ? valueArray : [...valueArray, choice];
  } else {
    // Remove choice
    return valueArray.filter((item) => item !== choice);
  }
}
