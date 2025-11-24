import { writable } from "svelte/store";
import type { AppSettings } from "$pytauri/_apiTypes";
import type { ProfileProps } from "$lib/menu/model";
export const appSettings = writable<null|AppSettings>(null)
export const debugLogLevelOverwrite  = writable<boolean>(false);
export const profileStore = writable<ProfileProps>({
  activeProfile: 0,
  states: [],
})
