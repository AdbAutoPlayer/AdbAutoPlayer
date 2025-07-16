package process

import (
	"adb-auto-player/internal/app"
	"adb-auto-player/internal/event_names"
	"adb-auto-player/internal/ipc"
	"adb-auto-player/internal/logger"
	"context"
	"encoding/json"
	"github.com/gorilla/websocket"
	"github.com/wailsapp/wails/v3/pkg/application"
	"os/exec"
	"strconv"
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
	ctx                context.Context
	cancel             context.CancelFunc
}

func NewWebSocketManager(isDev bool, port int, pythonBinaryPath string) *WebSocketManager {
	ws := &WebSocketManager{
		port:             port,
		pythonBinaryPath: pythonBinaryPath,
		isDev:            isDev,
	}
	ws.startWebSocketServer()
	return ws
}

func (ws *WebSocketManager) startWebSocketServer() {
	// TODO
}

func (ws *WebSocketManager) killServer() {
	// TODO
}

func (pm *WebSocketManager) connectWebSocket() {
	for {
		select {
		case <-pm.ctx.Done():
			return
		default:
			conn, _, err := websocket.DefaultDialer.Dial("ws://localhost:"+strconv.Itoa(pm.port), nil)
			if err != nil {
				logger.Get().Errorf("WebSocket connection failed: %v, retrying in 2s", err)
				time.Sleep(2 * time.Second)
				continue
			}
			pm.mutex.Lock()
			pm.conn = conn
			pm.mutex.Unlock()
			go pm.readWebSocket()
			return
		}
	}
}

func (pm *WebSocketManager) readWebSocket() {
	defer func() {
		pm.mutex.Lock()
		if pm.conn != nil {
			pm.conn.Close()
			pm.conn = nil
		}
		pm.mutex.Unlock()
	}()

	for {
		select {
		case <-pm.ctx.Done():
			return
		default:
			_, message, webSocketErr := pm.conn.ReadMessage()
			if webSocketErr != nil {
				logger.Get().Errorf("WebSocket read error: %v, reconnecting", webSocketErr)
				go pm.connectWebSocket()
				return
			}
			if len(strings.TrimSpace(string(message))) == 0 {
				continue
			}

			var summaryMessage ipc.Summary
			if err := json.Unmarshal(message, &summaryMessage); err == nil && summaryMessage.SummaryMessage != "" {
				pm.mutex.Lock()
				pm.summary = &summaryMessage
				pm.mutex.Unlock()
				app.EmitEvent(&application.CustomEvent{Name: event_names.WriteSummaryToLog, Data: pm.summary})
				continue
			}

			var logMessage ipc.LogMessage
			if err := json.Unmarshal(message, &logMessage); err == nil {
				logger.Get().LogMessage(logMessage)
				pm.mutex.Lock()
				pm.lastLogMessage = &logMessage
				pm.mutex.Unlock()
				app.EmitEvent(&application.CustomEvent{Name: event_names.LogMessage, Data: logMessage})
				continue
			}

			//var taskResponse ipc.TaskResponse
			//if webSocketErr := json.Unmarshal(message, &taskResponse); webSocketErr == nil && len(taskResponse.Tasks) > 0 {
			//	app.EmitEvent(&application.CustomEvent{Name: event_names.TaskUpdate, Data: taskResponse})
			//	continue
			//}

			logger.Get().Debugf("Skipping non-JSON WebSocket message: %s", string(message))
		}
	}
}

func (wm *WebSocketManager) getCommand(args ...string) (*exec.Cmd, error) {
	return getCommand(wm.isDev, wm.pythonBinaryPath, args...)
}
