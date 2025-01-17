interface MenuButton {
  label: string;
  callback: (...args: any[]) => void;
  active: boolean;
  alwaysEnabled?: boolean;
}

type LogLevel = "TRACE" | "DEBUG" | "INFO" | "WARNING" | "ERROR" | "FATAL";

interface LogMessage {
  level: LogLevel;
  message: string;
  timestamp: string;
  sourceFile?: string;
  lineNumber?: number;
}
