package main

import (
	"adb-auto-player/internal/ipc"
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"sync"
)

type Manager struct {
	mutex   sync.Mutex
	running *os.Process
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
		return fmt.Errorf("failed to get current working directory: %w", err)
	}
	pm.logger.Debugf("Binary path: %s/%s", workingDir, binaryPath)
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

	go func() {
		scanner := bufio.NewScanner(stdoutPipe)
		scanner.Buffer(make([]byte, 4096), 1024*1024)

		for scanner.Scan() {
			line := scanner.Text()
			var logMessage ipc.LogMessage
			if err := json.Unmarshal([]byte(line), &logMessage); err != nil {
				pm.logger.Error("Failed to parse JSON log message: " + err.Error())
				continue
			}

			pm.logger.LogMessage(logMessage)
		}

		if err := scanner.Err(); err != nil {
			if strings.Contains(err.Error(), "file already closed") {
				// Suppress logging for this error
				return
			}
			pm.logger.Error("Error while reading stdout: " + err.Error())
		}
	}()

	pm.running = cmd.Process

	go func() {
		err := cmd.Wait()
		if err != nil {
			pm.logger.Error("Process ended with error: " + err.Error())
		}

		pm.mutex.Lock()
		pm.running = nil
		pm.mutex.Unlock()
	}()

	return nil
}

func (pm *Manager) TerminateProcess() (bool, error) {
	pm.mutex.Lock()
	defer pm.mutex.Unlock()

	if pm.running == nil || !pm.isProcessRunning() {
		return false, nil
	}
	if err := pm.running.Kill(); err != nil {
		return false, err
	}

	_, err := pm.running.Wait()
	if err != nil {
		pm.running = nil
		return false, err
	}

	pm.running = nil
	return true, nil
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

	process, err := os.FindProcess(pm.running.Pid)
	if err != nil || process == nil {
		return false
	}

	return true
}
