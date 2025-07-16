package process

import (
	"adb-auto-player/internal/logger"
	"adb-auto-player/internal/settings"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"sync"
	"time"
)

type IPCService struct {
	mutex            sync.Mutex
	WebSocketManager *WebSocketManager
	STDIOManager     *STDIOManager
	IsDev            bool
	pythonBinaryPath string
}

var (
	serviceInstance *IPCService
	serviceOnce     sync.Once
)

func GetService() *IPCService {
	serviceOnce.Do(func() {
		serviceInstance = &IPCService{}
	})
	return serviceInstance
}

func (s *IPCService) GetPythonBinaryPath() string {
	return s.pythonBinaryPath
}

func (s *IPCService) SetPythonBinaryPath(pythonBinaryPath string) {
	s.pythonBinaryPath = pythonBinaryPath
	s.InitializeManager()
}

// InitializeManager will be called when Service is initialized or GeneralSettings gets updated.
func (s *IPCService) InitializeManager() {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	if settings.GetService().GetGeneralSettings().Advanced.DisableWebSockets {
		s.initializeSTDIOManager()
		return
	}

	if err := s.initializeWebSocketManager(); err != nil {
		logger.Get().Errorf("Failed to initialize WebSocketManager: '%v' using fallback", err)
		s.initializeSTDIOManager()
	}
}

func (s *IPCService) initializeSTDIOManager() {
	if nil != s.WebSocketManager {
		s.WebSocketManager.killServer()
		s.WebSocketManager = nil
	}
	if nil == s.STDIOManager {
		s.STDIOManager = NewSTDIOManager(
			s.IsDev,
			s.pythonBinaryPath,
		)
	}
}

func (s *IPCService) initializeWebSocketManager() error {
	s.STDIOManager = nil
	if nil == s.WebSocketManager {
		return s.setWebSocketManager()
	}

	if settings.GetService().GetGeneralSettings().Advanced.WebSocketPort != s.WebSocketManager.port {
		s.WebSocketManager.killServer()
		return s.setWebSocketManager()
	}
	return nil
}

func (s *IPCService) setWebSocketManager() error {
	wsm, err := NewWebSocketManager(s.IsDev, settings.GetService().GetGeneralSettings().Advanced.WebSocketPort, s.pythonBinaryPath)
	if nil != err {
		return err
	}
	s.WebSocketManager = wsm
	return nil
}

func (s *IPCService) StopTask(msg ...string) {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	if s.WebSocketManager != nil {
		// s.WebSocketManager.write(...)
	} else if s.STDIOManager != nil {
		s.STDIOManager.KillProcess()
	}

	message := "Stopping"
	if len(msg) > 0 {
		message = msg[0]
	}
	logger.Get().Warningf("%s", message)
	time.Sleep(2 * time.Second)
}

func (s *IPCService) StartTask(args []string, notifyWhenTaskEnds bool) error {
	s.mutex.Lock()
	defer s.mutex.Unlock()
	if s.WebSocketManager != nil {
		// s.WebSocketManager.write(...)
	}
	if s.STDIOManager != nil {
		return s.STDIOManager.StartProcess(args, notifyWhenTaskEnds)
	}
	return errors.New("no IPC Process Manager is running")
}

func (s *IPCService) IsTaskRunning() bool {
	s.mutex.Lock()
	defer s.mutex.Unlock()
	if s.WebSocketManager != nil {
		// s.WebSocketManager.write(...)
	}
	if s.STDIOManager != nil {
		return s.STDIOManager.isProcessRunning()
	}
	return false
}

func (s *IPCService) Exec(args []string) (string, error) {
	s.mutex.Lock()
	defer s.mutex.Unlock()
	if s.WebSocketManager != nil {
		// s.WebSocketManager.write(...)
	}

	if s.STDIOManager != nil {
		return s.STDIOManager.Exec(args...)
	}

	return "", errors.New("no IPC Process Manager is running")
}

func (s *IPCService) Shutdown() {
	s.StopTask()
	if s.WebSocketManager != nil {
		s.WebSocketManager.killServer()
	}
}

func getCommand(isDev bool, name string, args ...string) (*exec.Cmd, error) {
	if isDev {
		if _, err := os.Stat(name); os.IsNotExist(err) {
			return nil, fmt.Errorf("dev Python dir does not exist: %s", name)
		}

		uvPath, err := exec.LookPath("uv")
		if err != nil {
			return nil, fmt.Errorf("uv not found in PATH: %w", err)
		}

		cmd := exec.Command(uvPath, append([]string{"run", "adb-auto-player"}, args...)...)
		cmd.Dir = name

		return cmd, nil
	}

	return exec.Command(name, args...), nil
}
