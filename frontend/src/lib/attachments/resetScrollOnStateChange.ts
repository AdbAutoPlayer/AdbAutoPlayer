/**
 * Creates an attachment that resets the scrollTop of an element when a specified state changes.
 * @param obj A $state obj that returns the state to monitor for changes.
 * @returns An attachment function that resets scrollTop when the state changes.
 */
export function resetScrollOnStateChange(obj: any) {
  return (element: HTMLElement) => {
    const ignore = obj; // Causes state changes to trigger this function
    const maxScrollTop = element.scrollHeight - element.clientHeight;
    if (element.scrollTop > maxScrollTop && maxScrollTop >= 0) {
      element.scrollTop = 0;
    }
  };
}
