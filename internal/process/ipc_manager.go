package process

import (
	"adb-auto-player/internal/app"
	"adb-auto-player/internal/event_names"
	"adb-auto-player/internal/ipc"
	"adb-auto-player/internal/logger"
	"adb-auto-player/internal/notifications"
	"adb-auto-player/internal/settings"
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/gorilla/websocket"
	"github.com/shirou/gopsutil/process"
	"github.com/wailsapp/wails/v3/pkg/application"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"
)

// IPCManager handles both server process management and WebSocket communication.
type IPCManager struct {
	isDev            bool
	pythonBinaryPath string

	// Server management
	serverProcess                  *process.Process
	serverRunningInSeparateProcess bool

	// WebSocket connection management
	wsConn      *websocket.Conn
	wsConnected bool

	sendNotificationWhenTaskEnds bool
	summary                      *ipc.Summary
	lastLogMessage               *ipc.LogMessage

	websocketMutex sync.Mutex
	serverMutex    sync.Mutex

	logFile *os.File
}

type WebSocketCommandRequest struct {
	Type    string   `json:"type"`
	Command []string `json:"command"`
}

type WebSocketStopRequest struct {
	Type string `json:"type"`
}

// HealthCheckResponse represents the expected response from the /health endpoint.
type HealthCheckResponse struct {
	Detail string `json:"detail"`
}

func NewIPCManager(isDev bool, pythonBinaryPath string) *IPCManager {
	return &IPCManager{
		isDev:            isDev,
		pythonBinaryPath: pythonBinaryPath,
	}
}

// sendGET sends a GET request to the specified endpoint.
func (pm *IPCManager) sendGET(endpoint string) (*http.Response, error) {
	client := &http.Client{
		Timeout: 2 * time.Second,
	}

	serverUrl := fmt.Sprintf(
		"http://%s:%d%s",
		settings.GetService().GetGeneralSettings().Advanced.AutoPlayerHost,
		settings.GetService().GetGeneralSettings().Advanced.AutoPlayerPort,
		endpoint,
	)

	resp, err := client.Get(serverUrl)
	if err != nil {
		return nil, fmt.Errorf("failed to send GET request to %s: %w", endpoint, err)
	}

	return resp, nil
}

// healthCheck verifies if the correct server is running by checking the /health endpoint.
func (pm *IPCManager) healthCheck() (bool, error) {
	resp, err := pm.sendGET("/health")
	if err != nil {
		return false, err
	}
	defer func() {
		if err = resp.Body.Close(); err != nil {
			logger.Get().Errorf("resp.Body.Close error: %v", err)
		}
	}()

	if resp.StatusCode != http.StatusOK {
		return false, fmt.Errorf("health check returned non-OK status: %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return false, fmt.Errorf("failed to read health check response: %w", err)
	}

	var healthResp HealthCheckResponse
	if err = json.Unmarshal(body, &healthResp); err != nil {
		return false, fmt.Errorf("failed to parse health check response: %w", err)
	}

	if healthResp.Detail != "ADB Auto Player Server" {
		return false, fmt.Errorf("invalid health check response: expected detail='ADB Auto Player Server', got '%s'", healthResp.Detail)
	}

	return true, nil
}

// checkPortInUse checks if the specified host and port are already in use.
func (pm *IPCManager) checkPortInUse() (bool, error) {
	host := settings.GetService().GetGeneralSettings().Advanced.AutoPlayerHost
	port := settings.GetService().GetGeneralSettings().Advanced.AutoPlayerPort
	addr := fmt.Sprintf("%s:%d", host, port)

	listener, err := net.Listen("tcp", addr)
	if err != nil {
		if strings.Contains(err.Error(), "address already in use") || strings.Contains(err.Error(), "bind:") {
			return true, nil
		}
		return false, fmt.Errorf("failed to check port %s: %w", addr, err)
	}
	_ = listener.Close()
	return false, nil
}

// startServer starts the FastAPI server process.
func (pm *IPCManager) startServer() error {
	cmd, err := getUVDevCommand(pm.isDev, pm.pythonBinaryPath, "--server")
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
	pm.serverProcess = proc
	pm.serverRunningInSeparateProcess = false

	return nil
}

// startOrResolveServer attempts to use an existing server or start a new one.
func (pm *IPCManager) startOrResolveServer() error {
	pm.serverMutex.Lock()
	defer pm.serverMutex.Unlock()
	host := settings.GetService().GetGeneralSettings().Advanced.AutoPlayerHost
	port := settings.GetService().GetGeneralSettings().Advanced.AutoPlayerPort

	if pm.isServerRunning() {
		return nil
	}

	inUse, err := pm.checkPortInUse()
	if err != nil {
		logger.Get().Errorf("Failed to check if port %s:%d is in use: %v", host, port, err)
		return fmt.Errorf("failed to check port availability: %w", err)
	}

	if inUse {
		isValid, err2 := pm.healthCheck()
		if isValid && err2 == nil {
			if !pm.serverRunningInSeparateProcess {
				logger.Get().Infof("AutoPlayer Server found running on %s:%d", host, port)
			}
			pm.serverRunningInSeparateProcess = true
			return nil
		}
		return fmt.Errorf(
			"address %s:%d is used by another app, try changing the 'AutoPlayer Host' in General Settings - Advanced to any other number between 49152-65535",
			host,
			port,
		)
	}

	if err = pm.startServer(); err != nil {
		return fmt.Errorf("failed to start AutoPlayer Server on %s:%d: %v", host, port, err)

	}

	// Wait for the server to respond to /health endpoint
	timeout := time.After(30 * time.Second)
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-timeout:
			logger.Get().Errorf("Failed to start AutoPlayer Server on %s:%d: timeout waiting for health check", host, port)
			killProcessTree(pm.serverProcess)
			pm.serverProcess = nil
			return fmt.Errorf("failed to start AutoPlayer Server")
		case <-ticker.C:
			isValid, err2 := pm.healthCheck()
			if isValid && err2 == nil {
				logger.Get().Infof("AutoPlayer Server started")
				return nil
			}
		}
	}
}

// stopServer stops the FastAPI server process.
func (pm *IPCManager) stopServer() {
	if pm.serverRunningInSeparateProcess {
		logger.Get().Debugf("Not stopping server as it's running in a separate process")
		return
	}

	if pm.serverProcess == nil {
		return
	}

	killProcessTree(pm.serverProcess)
	pm.serverProcess = nil
}

// isServerRunning checks if the server process is running.
func (pm *IPCManager) isServerRunning() bool {
	if pm.serverRunningInSeparateProcess {
		isValid, err := pm.healthCheck()
		if isValid && err == nil {
			return true
		}
		pm.serverRunningInSeparateProcess = false
		return false
	}

	if pm.serverProcess == nil {
		return false
	}

	running, _ := pm.serverProcess.IsRunning()
	if !running {
		pm.serverProcess = nil
	}
	return running
}

// connectWebSocket establishes a WebSocket connection to the server.
func (pm *IPCManager) connectWebSocket() error {
	if pm.wsConnected && pm.wsConn != nil {
		return nil
	}

	host := settings.GetService().GetGeneralSettings().Advanced.AutoPlayerHost
	port := settings.GetService().GetGeneralSettings().Advanced.AutoPlayerPort

	u := url.URL{
		Scheme: "ws",
		Host:   fmt.Sprintf("%s:%d", host, port),
		Path:   "/ws",
	}

	conn, _, err := websocket.DefaultDialer.Dial(u.String(), nil)
	if err != nil {
		return fmt.Errorf("failed to connect to WebSocket: %w", err)
	}

	pm.wsConn = conn
	pm.wsConnected = true

	go pm.readWebSocketMessages()

	return nil
}

// readWebSocketMessages reads log messages from the WebSocket connection.
func (pm *IPCManager) readWebSocketMessages() {
	defer func() {
		pm.websocketMutex.Lock()
		pm.wsConnected = false
		pm.websocketMutex.Unlock()

		pm.taskEnded()
	}()

	for {
		_, message, err := pm.wsConn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) && !websocket.IsCloseError(err, websocket.CloseNormalClosure) {
				logger.Get().Errorf("WebSocket error: %v", err)
			}
			break
		}

		var logMessage ipc.LogMessage
		if err = unmarshalStrict(message, &logMessage); err == nil {
			pm.handleLogMessage(logMessage)
			continue
		}

		var summaryMessage ipc.Summary
		if err = unmarshalStrict(message, &summaryMessage); err == nil {
			if summaryMessage.SummaryMessage != "" {
				pm.summary = &summaryMessage
			}
			continue
		}

		logger.Get().Debugf("Received unknown WebSocket message: %s", string(message))
	}
}

func unmarshalStrict(data []byte, v interface{}) error {
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	return decoder.Decode(v)
}

// handleLogMessage processes a log message received from WebSocket.
func (pm *IPCManager) handleLogMessage(logMessage ipc.LogMessage) {
	if pm.logFile != nil {
		messageJson, _ := json.Marshal(logMessage)
		if _, err := fmt.Fprintln(pm.logFile, string(messageJson)); err != nil {
			logger.Get().Errorf("Failed to write to log file: %v", err)
		}
	}

	logger.Get().LogMessage(logMessage)
	pm.lastLogMessage = &logMessage
}

// setupLogFile creates a log file for the current command execution.
func (pm *IPCManager) setupLogFile(args []string) error {
	if settings.GetService().GetGeneralSettings().Logging.TaskLogLimit <= 0 {
		return nil
	}

	debugDir := "debug"
	if err := os.MkdirAll(debugDir, 0755); err != nil {
		logger.Get().Errorf("Failed to create debug directory: %v", err)
		return err
	}

	timestamp := time.Now().Format("20060102_150405")
	sanitizedArgs := strings.Join(args, "_")
	sanitizedArgs = regexp.MustCompile(`[^a-zA-Z0-9_-]`).ReplaceAllString(sanitizedArgs, "")
	logFileName := fmt.Sprintf("%s_%s.log", timestamp, sanitizedArgs)
	logFilePath := filepath.Join(debugDir, logFileName)

	logFile, err := os.Create(logFilePath)
	if err != nil {
		logger.Get().Errorf("Failed to create log file: %v", err)
		return err
	}

	pm.logFile = logFile

	// Clean up old log files if needed
	if settings.GetService().GetGeneralSettings().Logging.TaskLogLimit > 0 {
		files, err2 := filepath.Glob(filepath.Join(debugDir, "*.log"))
		if err2 == nil && len(files) > settings.GetService().GetGeneralSettings().Logging.TaskLogLimit {
			sort.Slice(files, func(i, j int) bool {
				infoI, _ := os.Stat(files[i])
				infoJ, _ := os.Stat(files[j])
				return infoI.ModTime().Before(infoJ.ModTime())
			})

			filesToDelete := len(files) - settings.GetService().GetGeneralSettings().Logging.TaskLogLimit
			for i := 0; i < filesToDelete; i++ {
				if err = os.Remove(files[i]); err != nil {
					logger.Get().Debugf("Failed to delete old log file %s: %v", files[i], err)
				}
			}
		}
	}

	return nil
}

// closeLogFile closes the current log file.
func (pm *IPCManager) closeLogFile() {
	if pm.logFile != nil {
		_ = pm.logFile.Close()
		pm.logFile = nil
	}
}

// StartTask starts a command execution via WebSocket.
func (pm *IPCManager) StartTask(args []string, notifyWhenTaskEnds bool, logLevel ...uint32) error {
	pm.websocketMutex.Lock()
	defer pm.websocketMutex.Unlock()

	originalLogLevel := logger.Get().GetLogLevel()
	if len(logLevel) > 0 {
		logger.Get().SetLogLevel(logLevel[0])
	}

	defer func() {
		if len(logLevel) > 0 {
			go func() {
				for pm.isTaskRunning() {
					time.Sleep(100 * time.Millisecond)
				}
				logger.Get().SetLogLevel(originalLogLevel)
			}()
		}
	}()

	if err := pm.startOrResolveServer(); err != nil {
		return fmt.Errorf("failed to start or resolve server: %w", err)
	}

	if err := pm.connectWebSocket(); err != nil {
		return fmt.Errorf("failed to connect to WebSocket: %w", err)
	}

	if err := pm.setupLogFile(args); err != nil {
		logger.Get().Errorf("Failed to setup log file: %v", err)
	}

	pm.sendNotificationWhenTaskEnds = notifyWhenTaskEnds
	pm.summary = nil
	pm.lastLogMessage = nil

	commandRequest := WebSocketCommandRequest{
		Type:    "execute_command",
		Command: args,
	}

	if err := pm.wsConn.WriteJSON(commandRequest); err != nil {
		pm.closeLogFile()
		return fmt.Errorf("failed to send command via WebSocket: %w", err)
	}

	return nil
}

// StopTask stops the current command execution.
func (pm *IPCManager) StopTask() {
	pm.websocketMutex.Lock()
	defer pm.websocketMutex.Unlock()

	if pm.wsConn == nil {
		return
	}

	pm.sendNotificationWhenTaskEnds = false
	stopRequest := WebSocketStopRequest{
		Type: "stop",
	}

	if err := pm.wsConn.WriteJSON(stopRequest); err != nil {
		if err.Error() != "websocket: close sent" {
			// can happen when changing host/port in general settings it is not a real problem.
			logger.Get().Errorf("Failed to send stop command via WebSocket: %v", err)
		}
	}

	pm.closeLogFile()

	if pm.wsConn != nil {
		err := pm.wsConn.Close()
		if err != nil {
			return
		}
		pm.wsConn = nil
		pm.wsConnected = false
	}
}

// isTaskRunning returns whether a command is currently running.
func (pm *IPCManager) isTaskRunning() bool {
	pm.websocketMutex.Lock()
	defer pm.websocketMutex.Unlock()

	if !pm.wsConnected || pm.wsConn == nil {
		return false
	}

	if err := pm.wsConn.WriteMessage(websocket.PingMessage, nil); err != nil {
		pm.wsConnected = false
		if pm.wsConn != nil {
			err = pm.wsConn.Close()
			if err != nil {
				return false
			}
			pm.wsConn = nil
		}
		return false
	}
	return pm.wsConnected
}

// taskEnded handles cleanup when a command execution ends.
func (pm *IPCManager) taskEnded() {
	pm.taskEndedNotification()
	pm.closeLogFile()

	pm.summary = nil
	pm.lastLogMessage = nil
	pm.sendNotificationWhenTaskEnds = false
}

func (pm *IPCManager) taskEndedNotification() {
	if pm.sendNotificationWhenTaskEnds {
		if pm.lastLogMessage != nil && pm.lastLogMessage.Level == ipc.LogLevelError {
			notifications.GetService().SendNotification("Task exited with Error", pm.lastLogMessage.Message)
		} else {
			summaryMessage := ""
			if pm.summary != nil {
				summaryMessage = pm.summary.SummaryMessage
			}
			notifications.GetService().SendNotification("Task ended", summaryMessage)
		}
	}
	app.EmitEvent(&application.CustomEvent{Name: event_names.WriteSummaryToLog, Data: pm.summary})
	app.Emit(event_names.TaskStopped)
}

// POSTCommand sends a command via HTTP.
func (pm *IPCManager) POSTCommand(args []string) ([]ipc.LogMessage, error) {
	if err := pm.startOrResolveServer(); err != nil {
		return nil, err
	}

	commandRequest := struct {
		Command []string `json:"command"`
	}{Command: args}

	responseBody, err := pm.sendPOST("/execute", commandRequest)
	if err != nil {
		return nil, err
	}

	var logResponse struct {
		Messages []ipc.LogMessage `json:"messages"`
	}
	if err = json.Unmarshal(responseBody, &logResponse); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return logResponse.Messages, nil
}

// sendPOST sends a POST request to the server.
func (pm *IPCManager) sendPOST(endpoint string, requestBody interface{}) ([]byte, error) {
	client := &http.Client{
		Timeout: 30 * time.Second,
	}

	body, err := json.Marshal(requestBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request body: %w", err)
	}

	serverUrl := fmt.Sprintf(
		"http://%s:%d%s",
		settings.GetService().GetGeneralSettings().Advanced.AutoPlayerHost,
		settings.GetService().GetGeneralSettings().Advanced.AutoPlayerPort,
		endpoint,
	)

	resp, err := client.Post(serverUrl, "application/json", bytes.NewBuffer(body))
	if err != nil {
		return nil, fmt.Errorf("failed to send POST request to %s: %w", endpoint, err)
	}
	defer func() {
		if err = resp.Body.Close(); err != nil {
			logger.Get().Errorf("resp.Body.Close error: %v", err)
		}
	}()

	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("server returned non-OK status: %d, response: %s", resp.StatusCode, string(responseBody))
	}

	return responseBody, nil
}

// Cleanup gracefully shuts down the IPC manager.
func (pm *IPCManager) Cleanup() {
	pm.StopTask()
	pm.stopServer()
	pm.closeLogFile()
}

// Helper function to kill process tree (moved from original code)
func killProcessTree(p *process.Process) {
	children, err := p.Children()
	if err != nil && !errors.Is(err, process.ErrorNoChildren) {
		logger.Get().Debugf("Failed to get children of process %d: %v", p.Pid, err)
	}

	for _, child := range children {
		killProcessTree(child)
	}

	if err = p.Kill(); err != nil {
		if strings.Contains(err.Error(), "no such process") {
			logger.Get().Debugf("Process %d already exited", p.Pid)
		} else {
			logger.Get().Errorf("Failed to kill process %d: %v", p.Pid, err)
		}
	}
}
