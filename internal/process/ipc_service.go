package process

import (
	"adb-auto-player/internal/logger"
	"adb-auto-player/internal/settings"
	"errors"
	"sync"
	"time"
)

type IPCService struct {
	mutex            sync.Mutex
	webSocketManager *WebSocketManager
	stdioManager     *STDIOManager
	IsDev            bool
	pythonBinaryPath *string
}

var (
	serviceInstance *IPCService
	serviceOnce     sync.Once
)

func GetService() *IPCService {
	serviceOnce.Do(func() {
		serviceInstance = &IPCService{}
		serviceInstance.InitializeManager()
	})
	return serviceInstance
}

// InitializeManager will be called when Service is initialized or GeneralSettings gets updated.
func (s *IPCService) InitializeManager() {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	if settings.GetService().GetGeneralSettings().Advanced.DisableWebSockets {
		if nil != s.webSocketManager {
			s.webSocketManager.killServer()
			s.webSocketManager = nil
		}
		if nil == s.stdioManager {
			s.stdioManager = NewSTDIOManager(s.IsDev)
		}
		return
	}

	s.stdioManager = nil
	if nil == s.webSocketManager {
		s.setNewWebSocketManager()
		return
	}

	if settings.GetService().GetGeneralSettings().Advanced.WebSocketPort != s.webSocketManager.port {
		s.webSocketManager.killServer()
		s.setNewWebSocketManager()
	}
}

func (s *IPCService) setNewWebSocketManager() *WebSocketManager {
	return NewWebSocketManager(s.pythonBinaryPath, settings.GetService().GetGeneralSettings().Advanced.WebSocketPort)
}

func (s *IPCService) StopTask(msg ...string) {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	if s.webSocketManager != nil {
		// s.webSocketManager.write(...)
	} else if s.stdioManager != nil {
		s.stdioManager.KillProcess()
	}

	message := "Stopping"
	if len(msg) > 0 {
		message = msg[0]
	}
	logger.Get().Warningf("%s", message)
	time.Sleep(2 * time.Second)
}

func (s *IPCService) StartTask(args []string, notifyWhenTaskEnds bool) error {
	if s.webSocketManager != nil {
		// s.webSocketManager.write(...)
	}
	if s.stdioManager != nil {
		return s.stdioManager.StartProcess(args, notifyWhenTaskEnds)
	}
	return errors.New("no IPC Process Manager is running")
}
