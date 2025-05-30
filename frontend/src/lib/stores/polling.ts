import { writable } from "svelte/store";
export const pollRunningGame = writable(false);
export const pollRunningProcess = writable(false);

export function enablePolling() {
  pollRunningGame.set(true);
  pollRunningProcess.set(true);
}

export function disablePolling() {
  pollRunningGame.set(false);
  pollRunningProcess.set(false);
}
