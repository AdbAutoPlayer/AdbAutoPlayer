package process

import (
	"adb-auto-player/internal/ipc"
	"adb-auto-player/internal/logger"
	"adb-auto-player/internal/settings"
	"bytes"
	"encoding/json"
	"fmt"
	"github.com/shirou/gopsutil/process"
	"io"
	"net/http"
	"sync"
	"time"
)

// ServerManager handles the server process and communication.
type ServerManager struct {
	isDev            bool
	pythonBinaryPath string
	process          *process.Process
	mutex            sync.Mutex
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

func (sm *ServerManager) stopServer() {
	if sm.process == nil {
		return
	}

	killProcessTree(sm.process)
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
	commandRequest := struct {
		Command []string `json:"command"`
	}{Command: args}

	responseBody, err := sm.sendPOST("/execute", commandRequest)
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

func (sm *ServerManager) sendPOST(endpoint string, requestBody interface{}) ([]byte, error) {
	client := &http.Client{
		Timeout: 10 * time.Second,
	}

	body, err := json.Marshal(requestBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request body: %w", err)
	}

	url := fmt.Sprintf(
		"http://%s:%d%s",
		settings.GetService().GetGeneralSettings().Advanced.AutoPlayerHost,
		settings.GetService().GetGeneralSettings().Advanced.AutoPlayerPort,
		endpoint,
	)

	resp, err := client.Post(url, "application/json", bytes.NewBuffer(body))
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
