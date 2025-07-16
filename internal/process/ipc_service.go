package process

import (
	"adb-auto-player/internal/app"
	"adb-auto-player/internal/event_names"
	"adb-auto-player/internal/ipc"
	"adb-auto-player/internal/logger"
	"adb-auto-player/internal/notifications"
	"errors"
	"fmt"
	"github.com/wailsapp/wails/v3/pkg/application"
	"os"
	"os/exec"
	"sync"
	"time"
)

type IPCService struct {
	mutex            sync.Mutex
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

	s.initializeSTDIOManager()
}

func (s *IPCService) initializeSTDIOManager() {
	if nil == s.STDIOManager {
		s.STDIOManager = NewSTDIOManager(
			s.IsDev,
			s.pythonBinaryPath,
		)
	}
}

func (s *IPCService) StopTask(msg ...string) {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	if s.STDIOManager != nil {
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

	if s.STDIOManager != nil {
		return s.STDIOManager.StartProcess(args, notifyWhenTaskEnds)
	}
	return errors.New("no IPC Process Manager is running")
}

func (s *IPCService) IsTaskRunning() bool {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	if s.STDIOManager != nil {
		return s.STDIOManager.isProcessRunning()
	}
	return false
}

func (s *IPCService) Exec(args []string) (string, error) {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	if s.STDIOManager != nil {
		return s.STDIOManager.Exec(args...)
	}

	return "", errors.New("no IPC Process Manager is running")
}

func (s *IPCService) Shutdown() {
	s.StopTask()
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

func taskEndedNotification(notifyWhenTaskEnds bool, lastLogMessage *ipc.LogMessage, summary *ipc.Summary) {
	if notifyWhenTaskEnds {
		if lastLogMessage != nil && lastLogMessage.Level == ipc.LogLevelError {
			notifications.GetService().SendNotification("Task exited with Error", lastLogMessage.Message)
		} else {
			summaryMessage := ""
			if summary != nil {
				summaryMessage = summary.SummaryMessage
			}
			notifications.GetService().SendNotification("Task ended", summaryMessage)
		}
	}
	app.EmitEvent(&application.CustomEvent{Name: event_names.WriteSummaryToLog, Data: summary})
	app.Emit(event_names.TaskStopped)
}
