import { writable } from "svelte/store";
export const pollRunningGame = writable(false);

export function enablePolling() {
  pollRunningGame.set(true);
}

export function disablePolling() {
  pollRunningGame.set(false);
}
