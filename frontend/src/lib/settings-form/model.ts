import { MenuOption } from "@wails/ipc";

export interface MenuButton {
  callback: (...args: any[]) => void;
  alwaysEnabled?: boolean;
  isProcessRunning: boolean;
  option: MenuOption;
}
