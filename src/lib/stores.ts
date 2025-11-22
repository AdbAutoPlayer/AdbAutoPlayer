import { writable } from "svelte/store";
import type { AppSettings } from "$pytauri/_apiTypes";
export const pollState = writable<boolean>(false);
export const appSettings = writable<null|AppSettings>(null)
export const debugLogLevelOverwrite  = writable<boolean>(false);
