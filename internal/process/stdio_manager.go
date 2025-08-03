package process

import (
	"adb-auto-player/internal/ipc"
	"adb-auto-player/internal/logger"
	"adb-auto-player/internal/settings"
	"bufio"
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/shirou/gopsutil/process"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"
)

type STDIOManager struct {
	isDev              bool
	pythonBinaryPath   string
	running            *process.Process
	notifyWhenTaskEnds bool
	summary            *ipc.Summary
	lastLogMessage     *ipc.LogMessage
	serverManager      *ServerManager // Embedded server manager
}

// ServerManager handles the server process and communication.
type ServerManager struct {
	isDev            bool
	pythonBinaryPath string
	process          *process.Process
	mutex            sync.Mutex
}

func NewSTDIOManager(isDev bool, pythonBinaryPath string) *STDIOManager {
	return &STDIOManager{
		isDev:            isDev,
		pythonBinaryPath: pythonBinaryPath,
		serverManager: &ServerManager{
			isDev:            isDev,
			pythonBinaryPath: pythonBinaryPath,
		},
	}
}

func (pm *STDIOManager) StartProcess(args []string, notifyWhenTaskEnds bool, logLevel ...uint32) error {
	if pm.running != nil {
		if pm.isProcessRunning() {
			return errors.New("a process is already running")
		}
	}

	cmd, err := pm.getCommand(args...)
	if err != nil {
		return err
	}

	if !pm.isDev {
		workingDir, err2 := os.Getwd()
		if err2 != nil {
			return err2
		}
		cmd.Dir = workingDir
	}

	stdoutPipe, err := cmd.StdoutPipe()
	if err != nil {
		return fmt.Errorf("failed to create stdout pipe: %w", err)
	}

	if err = cmd.Start(); err != nil {
		return fmt.Errorf("failed to start command: %w", err)
	}

	originalLogLevel := logger.Get().GetLogLevel()
	if len(logLevel) > 0 {
		logger.Get().SetLogLevel(logLevel[0])
	}

	logger.Get().Debugf("Started process with PID: %d", cmd.Process.Pid)
	proc, err := process.NewProcess(int32(cmd.Process.Pid))
	if err != nil {
		return fmt.Errorf("failed to create process handle: %w", err)
	}
	pm.running = proc
	pm.notifyWhenTaskEnds = notifyWhenTaskEnds
	debugDir := "debug"
	if err = os.MkdirAll(debugDir, 0755); err != nil {
		logger.Get().Errorf("Failed to create debug directory: %v", err)
	}

	timestamp := time.Now().Format("20060102_150405")
	sanitizedArgs := strings.Join(args, "_")
	sanitizedArgs = regexp.MustCompile(`[^a-zA-Z0-9_-]`).ReplaceAllString(sanitizedArgs, "")
	logFileName := fmt.Sprintf("%s_%s.log", timestamp, sanitizedArgs)
	logFilePath := filepath.Join(debugDir, logFileName)

	logFile, err := os.Create(logFilePath)
	if err != nil {
		logger.Get().Errorf("Failed to create log file: %v", err)
	}
	if settings.GetService().GetGeneralSettings().Logging.ActionLogLimit > 0 {
		files, err3 := filepath.Glob(filepath.Join(debugDir, "*.log"))
		if err3 == nil && len(files) > settings.GetService().GetGeneralSettings().Logging.ActionLogLimit {
			sort.Slice(files, func(i, j int) bool {
				infoI, _ := os.Stat(files[i])
				infoJ, _ := os.Stat(files[j])
				return infoI.ModTime().Before(infoJ.ModTime())
			})

			filesToDelete := len(files) - settings.GetService().GetGeneralSettings().Logging.ActionLogLimit
			for i := 0; i < filesToDelete; i++ {
				if err = os.Remove(files[i]); err != nil {
					logger.Get().Debugf("Failed to delete old log file %s: %v", files[i], err)
				}
			}
		}
	}

	go func() {
		scanner := bufio.NewScanner(stdoutPipe)
		scanner.Buffer(make([]byte, 4096), 1024*1024)

		for scanner.Scan() {
			line := scanner.Text()
			// Skip empty or invalid lines
			if strings.TrimSpace(line) == "" {
				continue
			}
			var summaryMessage ipc.Summary
			if err = json.Unmarshal([]byte(line), &summaryMessage); err == nil {
				if summaryMessage.SummaryMessage != "" {
					pm.summary = &summaryMessage
					continue
				}
			}
			// Write to file after Summary because the Summary data does not help with debugging.
			if logFile != nil {
				if _, err = fmt.Fprintln(logFile, line); err != nil {
					logger.Get().Errorf("Failed to write to log file: %v", err)
				}
			}

			var logMessage ipc.LogMessage
			if err = json.Unmarshal([]byte(line), &logMessage); err == nil {
				logger.Get().LogMessage(logMessage)
				pm.lastLogMessage = &logMessage
				continue
			}

			logger.Get().Debugf("Skipping non-JSON output: %s", line)
		}

		if err = scanner.Err(); err != nil {
			if !strings.Contains(err.Error(), "file already closed") {
				logger.Get().Errorf("Error while reading stdout: %v", err)
			}
		}
	}()

	go func() {
		_, err = cmd.Process.Wait()
		if err != nil {
			logger.Get().Errorf("Task ended with Error: %v", err)
		}

		logger.Get().SetLogLevel(originalLogLevel)
		pm.processEnded()
	}()

	return nil
}

func (pm *STDIOManager) KillProcess() {
	if pm.running == nil || !pm.isProcessRunning() {
		return
	}

	pm.notifyWhenTaskEnds = false

	killProcessTree(pm.running)
}

func killProcessTree(p *process.Process) {
	children, err := p.Children()
	if err != nil && !errors.Is(err, process.ErrorNoChildren) {
		logger.Get().Debugf("Failed to get children of process %d: %v", p.Pid, err)
	}

	for _, child := range children {
		killProcessTree(child) // recurse
	}

	if err = p.Kill(); err != nil {
		if strings.Contains(err.Error(), "no such process") {
			logger.Get().Debugf("Process %d already exited", p.Pid)
		} else {
			logger.Get().Errorf("Failed to kill process %d: %v", p.Pid, err)
		}
	}
}

func (pm *STDIOManager) isProcessRunning() bool {
	if pm.running == nil {
		return false
	}

	running, _ := pm.running.IsRunning()

	if !running {
		pm.processEnded()
	}

	return running
}

func (pm *STDIOManager) getCommand(args ...string) (*exec.Cmd, error) {
	return getCommand(pm.isDev, pm.pythonBinaryPath, args...)
}

func (pm *STDIOManager) Exec(args ...string) (string, []ipc.LogMessage, error) {
	messages, err := pm.ServerExec(args...)
	if err == nil {
		return "", messages, nil
	}
	result, err := pm.exec(args...)
	return result, messages, err
}

func (pm *STDIOManager) exec(args ...string) (string, error) {
	cmd, err := pm.getCommand(args...)
	if err != nil {
		return "", err
	}

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err = cmd.Run()

	if err != nil {
		output := stdout.String()
		errorOutput := stderr.String()

		if strings.Contains(errorOutput, "contains a virus") || strings.Contains(err.Error(), "contains a virus") {
			return "", fmt.Errorf("%w\nRead: https://AdbAutoPlayer.github.io/AdbAutoPlayer/user-guide/troubleshoot.html#file-contains-a-virus-or-potentially-unwanted-software", err)
		}

		lines := strings.Split(output, "\n")

		if len(lines) > 0 {
			var lastLine string
			for i := len(lines) - 1; i >= 0; i-- {
				lastLine = strings.TrimSpace(lines[i])
				if lastLine != "" {
					break
				}
			}

			var logMessage ipc.LogMessage
			if err = json.Unmarshal([]byte(lastLine), &logMessage); err == nil {
				return "", err
			}
		}

		if pm.isDev {
			return "", fmt.Errorf("failed to execute '%s': %w\nStdout: %s\nStderr: %s", pm.pythonBinaryPath, err, output, errorOutput)
		}

		logger.Get().Debugf("failed to execute '%s': %v\nStdout: %s\nStderr: %s", pm.pythonBinaryPath, err, output, errorOutput)

		return "", fmt.Errorf("failed to execute command: %w\nStderr: %s", err, errorOutput)
	}
	return stdout.String(), nil
}

func (pm *STDIOManager) ServerExec(args ...string) ([]ipc.LogMessage, error) {
	pm.serverManager.mutex.Lock()
	defer pm.serverManager.mutex.Unlock()
	if err := pm.serverManager.startServer(); err != nil {
		var logMessages []ipc.LogMessage
		return logMessages, err
	}
	return pm.serverManager.sendCommand(args)
}

func (pm *STDIOManager) processEnded() {
	taskEndedNotification(pm.notifyWhenTaskEnds, pm.lastLogMessage, pm.summary)
	pm.running = nil
	pm.summary = nil
	pm.lastLogMessage = nil
	pm.notifyWhenTaskEnds = false
}

// startServer starts a server process running 'python -m adb_auto_player --server'.
func (sm *ServerManager) startServer() error {
	if sm.process != nil && sm.isServerRunning() {
		return nil
	}
	cmd, err := getCommand(sm.isDev, sm.pythonBinaryPath, "--server")
	if err != nil {
		return fmt.Errorf("failed to get server command: %w", err)
	}

	if err = cmd.Start(); err != nil {
		return fmt.Errorf("failed to start server: %w", err)
	}
	logger.Get().Debugf("Started server with PID: %d", cmd.Process.Pid)

	proc, err := process.NewProcess(int32(cmd.Process.Pid))
	if err != nil {
		return fmt.Errorf("failed to create process handle: %w", err)
	}
	sm.process = proc

	// Give the server a moment to start up
	time.Sleep(1 * time.Second)

	return nil
}

func (sm *ServerManager) stopServer() error {
	if sm.process == nil {
		return nil
	}
	children, _ := sm.process.Children()
	for _, child := range children {
		_ = child.Kill()
	}

	err := sm.process.Kill()
	if err != nil {
		return fmt.Errorf("failed to kill process: %w", err)
	}

	return nil
}

// isServerRunning checks if the server process is running.
func (sm *ServerManager) isServerRunning() bool {
	if sm.process == nil {
		return false
	}

	running, _ := sm.process.IsRunning()
	if !running {
		sm.process = nil
	}
	return running
}

// sendCommand sends a POST request with CommandRequest to the FastAPI server.
func (sm *ServerManager) sendCommand(args []string) ([]ipc.LogMessage, error) {
	client := &http.Client{
		Timeout: 10 * time.Second,
	}
	commandRequest := struct {
		Command []string `json:"command"`
	}{Command: args}

	var logMessages []ipc.LogMessage

	body, err := json.Marshal(commandRequest)
	if err != nil {
		return logMessages, fmt.Errorf("failed to marshal command request: %w", err)
	}
	url := fmt.Sprintf(
		"http://%s:%d/execute",
		settings.GetService().GetGeneralSettings().Advanced.AutoPlayerHost,
		settings.GetService().GetGeneralSettings().Advanced.AutoPlayerPort,
	)
	resp, err := client.Post(url, "application/json", bytes.NewBuffer(body))
	if err != nil {
		return logMessages, fmt.Errorf("failed to send POST request: %w", err)
	}
	defer resp.Body.Close()

	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return logMessages, fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return logMessages, fmt.Errorf("server returned non-OK status: %d, response: %s", resp.StatusCode, string(responseBody))
	}

	var logResponse struct {
		Messages []ipc.LogMessage `json:"messages"`
	}
	if err = json.Unmarshal(responseBody, &logResponse); err != nil {
		fmt.Println("Still failed:", err)

		return logMessages, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return logResponse.Messages, nil
}
