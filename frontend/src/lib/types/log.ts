type LogLevel = "DEBUG" | "INFO" | "WARNING" | "ERROR" | "FATAL";

interface LogMessage {
  level: LogLevel;
  message: string;
  timestamp: string;
  source_file?: string;
  function_name?: string;
  line_number?: number;
  html_class?: string;
}
