package process

import (
	"adb-auto-player/internal/ipc"
	"adb-auto-player/internal/logger"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"sync"
)

type IPCService struct {
	mutex            sync.Mutex
	manager          *IPCManager
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

	if nil == s.manager || s.pythonBinaryPath != s.manager.pythonBinaryPath {
		s.manager = NewIPCManager(
			s.IsDev,
			s.pythonBinaryPath,
		)
	}
}

func (s *IPCService) StopTask(msg ...string) {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	if !s.manager.isTaskRunning() {
		return
	}

	if s.manager != nil {
		s.manager.StopTask()
	}

	message := "Stopping"
	if len(msg) > 0 {
		message = msg[0]
	}
	logger.Get().Warningf("%s", message)
}

func (s *IPCService) StartTask(args []string, notifyWhenTaskEnds bool, logLevel ...uint32) error {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	if s.manager != nil {
		return s.manager.StartTask(args, notifyWhenTaskEnds, logLevel...)
	}
	return errors.New("no IPC Process Manager is running")
}

func (s *IPCService) POSTCommand(args []string) ([]ipc.LogMessage, error) {
	if s.manager != nil {
		return s.manager.POSTCommand(args)
	}
	var logMessages []ipc.LogMessage
	return logMessages, errors.New("no IPC Process Manager is running")
}

func (s *IPCService) Shutdown() {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	if s.manager == nil {
		return
	}

	s.manager.Cleanup()
}

func (s *IPCService) SendPOST(endpoint string, requestBody interface{}) ([]byte, error) {
	if s.manager == nil {
		return nil, errors.New("no IPC Process Manager is running")
	}

	return s.manager.sendPOST(endpoint, requestBody)
}

func getUVDevCommand(isDev bool, name string, args ...string) (*exec.Cmd, error) {
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
