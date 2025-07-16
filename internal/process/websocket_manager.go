package process

import (
	"adb-auto-player/internal/ipc"
	"adb-auto-player/internal/logger"
	"fmt"
	"github.com/gorilla/websocket"
	"os"
	"os/exec"
	"strings"
	"sync"
	"time"
)

type WebSocketManager struct {
	port               int
	pythonBinaryPath   string
	mutex              sync.Mutex
	isDev              bool
	notifyWhenTaskEnds bool
	summary            *ipc.Summary
	lastLogMessage     *ipc.LogMessage
	conn               *websocket.Conn
	serverCmd          *exec.Cmd
}

func NewWebSocketManager(isDev bool, port int, pythonBinaryPath string) (*WebSocketManager, error) {
	ws := &WebSocketManager{
		port:             port,
		pythonBinaryPath: pythonBinaryPath,
		isDev:            isDev,
	}
	if err := ws.startWebSocketServer(); err != nil {
		return nil, err
	}
	return ws, nil
}

func (ws *WebSocketManager) startWebSocketServer() error {
	ws.mutex.Lock()
	defer ws.mutex.Unlock()

	// Get the command to start the WebSocket server
	cmd, err := ws.getCommand("StartServer", "--ws-port", fmt.Sprintf("%d", ws.port))
	if err != nil {
		return err
	}

	ws.serverCmd = cmd

	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	// Start the server in the background
	go func() {
		if errStart := cmd.Start(); errStart != nil {
			logger.Get().Errorf("Failed to start WebSocket server: %v", errStart)
			return
		}
		logger.Get().Debugf("WebSocket server started on port %d", ws.port)

		// Wait for the process to exit and log any errors
		if errWait := cmd.Wait(); errWait != nil && !strings.Contains(errWait.Error(), "signal: killed") {
			logger.Get().Errorf("WebSocket server exited with error: %v", errWait)
		}
	}()

	// Wait briefly to ensure the server starts
	time.Sleep(1 * time.Second)

	return ws.StartConnection()
}

func (ws *WebSocketManager) StartConnection() error {
	if ws.IsConnectionActive() {
		return nil
	}

	ws.mutex.Lock()
	defer ws.mutex.Unlock()
	url := fmt.Sprintf("ws://localhost:%d", ws.port)
	for attempts := 0; attempts < 5; attempts++ {
		conn, _, errDial := websocket.DefaultDialer.Dial(url, nil)
		if errDial == nil {
			ws.conn = conn
			logger.Get().Debugf("Connected to WebSocket server at %s", url)
			return nil
		}
		logger.Get().Warningf("Failed to connect to WebSocket server: %v, retrying...", errDial)
		time.Sleep(1 * time.Second)
	}

	return fmt.Errorf("failed to connect to WebSocket server after retries")
}

func (ws *WebSocketManager) killServer() {
	ws.mutex.Lock()
	defer ws.mutex.Unlock()

	if ws.conn != nil {
		if err := ws.conn.Close(); err != nil {
			logger.Get().Errorf("Error closing WebSocket connection: %v", err)
		}
		ws.conn = nil
	}

	if ws.serverCmd != nil && ws.serverCmd.Process != nil {
		if err := ws.serverCmd.Process.Kill(); err != nil {
			logger.Get().Errorf("Error killing WebSocket server process: %v", err)
		} else {
			logger.Get().Debugf("WebSocket server process terminated successfully")
		}
		// Wait for the process to exit to ensure cleanup
		if err := ws.serverCmd.Wait(); err != nil && !strings.Contains(err.Error(), "signal: killed") {
			logger.Get().Errorf("Error waiting for WebSocket server process to exit: %v", err)
		}
		ws.serverCmd = nil
	}
}

func (ws *WebSocketManager) getCommand(args ...string) (*exec.Cmd, error) {
	return getCommand(ws.isDev, ws.pythonBinaryPath, args...)
}

// SendMessage sends a JSON message to the WebSocket server
func (ws *WebSocketManager) SendMessage(message interface{}) error {
	if err := ws.StartConnection(); err != nil {
		return err
	}

	ws.mutex.Lock()
	defer ws.mutex.Unlock()

	if ws.conn == nil {
		return fmt.Errorf("no active WebSocket connection")
	}

	if err := ws.conn.WriteJSON(message); err != nil {
		logger.Get().Errorf("Failed to send WebSocket message: %v", err)
		return err
	}
	return nil
}

// IsConnectionActive checks if the WebSocket connection is active
func (ws *WebSocketManager) IsConnectionActive() bool {
	ws.mutex.Lock()
	defer ws.mutex.Unlock()

	if ws.conn == nil {
		return false
	}

	err := ws.conn.WriteControl(websocket.PingMessage, []byte{}, time.Now().Add(2*time.Second))
	return err == nil
}

func (ws *WebSocketManager) processEnded() {
	taskEndedNotification(ws.notifyWhenTaskEnds, ws.lastLogMessage, ws.summary)
	ws.summary = nil
	ws.lastLogMessage = nil
	ws.notifyWhenTaskEnds = false
}
