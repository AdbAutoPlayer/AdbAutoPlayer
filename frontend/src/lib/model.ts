import { ipc } from "$lib/wailsjs/go/models";

export interface MenuButton {
  callback: (...args: any[]) => void;
  alwaysEnabled?: boolean;
  isProcessRunning: boolean;
  option: ipc.MenuOption;
}
