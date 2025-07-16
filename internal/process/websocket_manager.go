package process

import (
	"adb-auto-player/internal/ipc"
	"adb-auto-player/internal/logger"
	"github.com/gorilla/websocket"
	"os/exec"
	"strings"
	"sync"
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
	cmd, err := ws.getCommand("StartServer")

	if err != nil {
		return err
	}

	ws.serverCmd = cmd

	// TODO run this in background
	return nil
}

func (ws *WebSocketManager) killServer() {
	ws.mutex.Lock()
	defer ws.mutex.Unlock()

	if ws.serverCmd != nil {
		return
	}

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

func (wm *WebSocketManager) getCommand(args ...string) (*exec.Cmd, error) {
	return getCommand(wm.isDev, wm.pythonBinaryPath, args...)
}
