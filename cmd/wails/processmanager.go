package main

import (
	"adb-auto-player/internal/ipc"
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/shirou/gopsutil/process"
	"os"
	"os/exec"
	stdruntime "runtime"
	"strings"
	"sync"
)

type Manager struct {
	mutex   sync.Mutex
	running *process.Process
	logger  *ipc.FrontendLogger
	blocked bool
}

var (
	instance *Manager
	once     sync.Once
)

func GetProcessManager() *Manager {
	once.Do(func() {
		instance = &Manager{}
	})
	return instance
}

func (pm *Manager) StartProcess(binaryPath string, args []string) error {
	pm.mutex.Lock()
	defer pm.mutex.Unlock()

	if pm.running != nil {
		if pm.isProcessRunning() {
			return errors.New("a process is already running")
		}
		pm.running = nil
	}

	workingDir, err := os.Getwd()
	if err != nil {
		return err
	}

	cmd := exec.Command(binaryPath, args...)
	cmd.Dir = workingDir
	stdoutPipe, err := cmd.StdoutPipe()
	if err != nil {
		return fmt.Errorf("failed to create stdout pipe: %w", err)
	}

	if err := cmd.Start(); err != nil {
		return fmt.Errorf("failed to start command: %w", err)
	}
	pm.logger.Debugf("Started process with PID: %d", cmd.Process.Pid)

	proc, err := process.NewProcess(int32(cmd.Process.Pid))
	if err != nil {
		return fmt.Errorf("failed to create process handle: %w", err)
	}
	pm.running = proc

	go func() {
		scanner := bufio.NewScanner(stdoutPipe)
		scanner.Buffer(make([]byte, 4096), 1024*1024)

		for scanner.Scan() {
			line := scanner.Text()
			var logMessage ipc.LogMessage
			if err := json.Unmarshal([]byte(line), &logMessage); err != nil {
				pm.logger.Errorf("Failed to parse JSON log message: %v", err)
				continue
			}

			pm.logger.LogMessage(logMessage)
		}

		if err := scanner.Err(); err != nil {
			if !strings.Contains(err.Error(), "file already closed") {
				pm.logger.Errorf("Error while reading stdout: %v", err)
			}
		}
	}()

	go func() {
		_, err := cmd.Process.Wait()
		if err != nil {
			pm.logger.Errorf("Process ended with error: %v", err)
		}

		pm.mutex.Lock()
		pm.running = nil
		pm.mutex.Unlock()
	}()

	return nil
}

func (pm *Manager) KillProcess() (bool, error) {
	pm.mutex.Lock()
	defer pm.mutex.Unlock()

	if pm.running == nil || !pm.isProcessRunning() {
		return false, nil
	}

	children, err := pm.running.Children()
	if err != nil && !errors.Is(err, process.ErrorNoChildren) {
		if stdruntime.GOOS == "darwin" && err.Error() == "exit status 1" {
			pm.logger.Debug("Ignoring exit status 1 for GOOS == darwin")
		} else {
			pm.logger.Errorf("Error getting child processes: %v", err)
		}
	}

	processName, nameErr := pm.running.Name()

	if err := pm.running.Kill(); err != nil {
		pm.logger.Errorf("Failed to kill process: %v", err)
	}

	for _, child := range children {
		if err := child.Kill(); err != nil {
			pm.logger.Errorf("Error killing child process %d: %v", child.Pid, err)
		}
	}

	if nameErr == nil {
		pm.killAllProcessesByName(processName)
	}

	pm.running = nil
	return true, nil
}

func (pm *Manager) killAllProcessesByName(processName string) {
	processes, err := process.Processes()
	if err != nil {
		pm.logger.Errorf("Failed to list processes: %v", err)
		return
	}

	for _, proc := range processes {
		name, err := proc.Name()
		if err != nil {
			continue
		}

		if name == processName {
			if err := proc.Kill(); err != nil {
				pm.logger.Errorf("Failed to kill process %d (%s): %v", proc.Pid, processName, err)
			} else {
				pm.logger.Debug(fmt.Sprintf("Killed process %d (%s)", proc.Pid, processName))
			}
		}
	}
}

func (pm *Manager) IsProcessRunning() bool {
	if pm.blocked {
		return true
	}
	pm.mutex.Lock()
	defer pm.mutex.Unlock()

	return pm.isProcessRunning()
}

func (pm *Manager) isProcessRunning() bool {
	if pm.running == nil {
		return false
	}

	running, err := pm.running.IsRunning()
	if err != nil {
		return false
	}

	return running
}

func (pm *Manager) Exec(binaryPath string, args ...string) (string, error) {
	cmd := exec.Command(binaryPath, args...)

	output, err := cmd.Output()
	if err != nil {
		if strings.Contains(err.Error(), "contains a virus") {
			return "", fmt.Errorf("%w Read: https://yulesxoxo.github.io/AdbAutoPlayer/user-guide/troubleshoot.html#file-contains-a-virus-or-potentially-unwanted-software", err)
		}
		return "", fmt.Errorf("failed to execute command: %w", err)
	}
	return string(output), nil
}
