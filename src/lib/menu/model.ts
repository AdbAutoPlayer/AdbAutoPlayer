import type { GameGUIOptions, MenuOption } from "$pytauri/_apiTypes";
import type { JSONSchema } from "json-schema-to-typescript";

export interface MenuButton {
  callback: (...args: any[]) => void;
  alwaysEnabled?: boolean;
  isProcessRunning: boolean;
  option: MenuOption;
}

export interface SettingsProps {
  showSettingsForm: boolean;
  formData: FormDataGeneric;
  formSchema: JSONSchema;
  fileName: string;
}

export interface ProfileState {
  activeGame: GameGUIOptions | null;
  activeTask: string | null;
  deviceId: string | null;
}

export interface ProfileProps {
  activeProfile: number;
  states: ProfileState[];
}

export interface PydanticSettingsFormResponse {
  0: FormDataGeneric,
  1: JSONSchema,
  2: string,
}

export interface RustSettingsFormResponse {
  settings: FormDataGeneric,
  schema: string,
  file_name: string,
}
