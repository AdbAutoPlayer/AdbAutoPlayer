package process

import (
	"adb-auto-player/internal/app"
	"adb-auto-player/internal/event_names"
	"adb-auto-player/internal/ipc"
	"adb-auto-player/internal/logger"
	"bufio"
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/shirou/gopsutil/process"
	"github.com/wailsapp/wails/v3/pkg/application"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"
)

type Manager struct {
	mutex          sync.Mutex
	running        *process.Process
	Blocked        bool
	IsDev          bool
	ActionLogLimit int
}

var (
	instance *Manager
	once     sync.Once
)

func Get() *Manager {
	once.Do(func() {
		instance = &Manager{}
	})
	return instance
}

func (pm *Manager) StartProcess(binaryPath *string, args []string, logLevel ...uint8) error {
	if nil == binaryPath {
		return errors.New("python binary not found")
	}
	pm.mutex.Lock()
	defer pm.mutex.Unlock()

	if pm.running != nil {
		if pm.isProcessRunning() {
			return errors.New("a process is already running")
		}
		pm.processEnded()
	}

	cmd, err := pm.getCommand(*binaryPath, args...)
	if err != nil {
		return err
	}

	if !pm.IsDev {
		workingDir, err := os.Getwd()
		if err != nil {
			return err
		}
		cmd.Dir = workingDir
	}

	stdoutPipe, err := cmd.StdoutPipe()
	if err != nil {
		return fmt.Errorf("failed to create stdout pipe: %w", err)
	}

	if err = cmd.Start(); err != nil {
		return fmt.Errorf("failed to start command: %w", err)
	}
	logger.Get().Debugf("Started process with PID: %d", cmd.Process.Pid)

	originalLogLevel := logger.Get().LogLevel
	if len(logLevel) > 0 {
		logger.Get().LogLevel = logLevel[0]
	}

	proc, err := process.NewProcess(int32(cmd.Process.Pid))
	if err != nil {
		return fmt.Errorf("failed to create process handle: %w", err)
	}
	pm.running = proc

	debugDir := "debug"
	if err = os.MkdirAll(debugDir, 0755); err != nil {
		logger.Get().Errorf("Failed to create debug directory: %v", err)
	}

	timestamp := time.Now().Format("20060102_150405")
	sanitizedArgs := strings.Join(args, "_")
	sanitizedArgs = regexp.MustCompile(`[^a-zA-Z0-9_-]`).ReplaceAllString(sanitizedArgs, "")
	logFileName := fmt.Sprintf("%s_%s.log", timestamp, sanitizedArgs)
	logFilePath := filepath.Join(debugDir, logFileName)

	logFile, err := os.Create(logFilePath)
	if err != nil {
		logger.Get().Errorf("Failed to create log file: %v", err)
	}
	if pm.ActionLogLimit > 0 {
		files, err := filepath.Glob(filepath.Join(debugDir, "*.log"))
		if err == nil && len(files) > pm.ActionLogLimit {
			sort.Slice(files, func(i, j int) bool {
				infoI, _ := os.Stat(files[i])
				infoJ, _ := os.Stat(files[j])
				return infoI.ModTime().Before(infoJ.ModTime())
			})

			filesToDelete := len(files) - pm.ActionLogLimit
			for i := 0; i < filesToDelete; i++ {
				if err = os.Remove(files[i]); err != nil {
					logger.Get().Debugf("Failed to delete old log file %s: %v", files[i], err)
				}
			}
		}
	}

	go func() {
		scanner := bufio.NewScanner(stdoutPipe)
		scanner.Buffer(make([]byte, 4096), 1024*1024)

		for scanner.Scan() {
			line := scanner.Text()
			var summaryMessage ipc.Summary
			if err = json.Unmarshal([]byte(line), &summaryMessage); err == nil {
				if summaryMessage.SummaryMessage != "" {
					app.EmitEvent(&application.CustomEvent{Name: event_names.SummaryMessage, Data: summaryMessage})
					continue
				}
			}
			// Write to file after Summary because the Summary data does not help with debugging.
			if logFile != nil {
				if _, err = fmt.Fprintln(logFile, line); err != nil {
					logger.Get().Errorf("Failed to write to log file: %v", err)
				}
			}

			var logMessage ipc.LogMessage
			if err = json.Unmarshal([]byte(line), &logMessage); err == nil {
				logger.Get().LogMessage(logMessage)
				continue
			}

			logger.Get().Errorf("Failed to parse JSON message: %v", err)
		}

		if err = scanner.Err(); err != nil {
			if !strings.Contains(err.Error(), "file already closed") {
				logger.Get().Errorf("Error while reading stdout: %v", err)
			}
		}
	}()

	go func() {
		_, err = cmd.Process.Wait()
		if err != nil {
			logger.Get().Errorf("Process ended with error: %v", err)
		}

		pm.mutex.Lock()
		logger.Get().LogLevel = originalLogLevel
		pm.processEnded()
		pm.mutex.Unlock()
	}()

	return nil
}

func (pm *Manager) KillProcess(msg ...string) {
	pm.mutex.Lock()
	defer pm.mutex.Unlock()

	if pm.running == nil || !pm.isProcessRunning() {
		return
	}

	killProcessTree(pm.running)

	message := "Stopping"
	if len(msg) > 0 {
		message = msg[0]
	}

	logger.Get().Warningf("%s", message)
	time.Sleep(2 * time.Second)
}

func killProcessTree(p *process.Process) {
	children, err := p.Children()
	if err != nil && !errors.Is(err, process.ErrorNoChildren) {
		logger.Get().Debugf("Failed to get children of process %d: %v", p.Pid, err)
	}

	for _, child := range children {
		killProcessTree(child) // recurse
	}

	if err = p.Kill(); err != nil {
		if strings.Contains(err.Error(), "no such process") {
			logger.Get().Debugf("Process %d already exited", p.Pid)
		} else {
			logger.Get().Errorf("Failed to kill process %d: %v", p.Pid, err)
		}
	}
}

func (pm *Manager) IsProcessRunning() bool {
	if pm.Blocked {
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

	if !running {
		pm.processEnded()
	}

	return running
}

func (pm *Manager) getCommand(name string, args ...string) (*exec.Cmd, error) {
	if pm.IsDev {
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

func (pm *Manager) Exec(binaryPath string, args ...string) (string, error) {
	cmd, err := pm.getCommand(binaryPath, args...)
	if err != nil {
		return "", err
	}

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err = cmd.Run()

	if err != nil {
		output := stdout.String()
		errorOutput := stderr.String()

		if strings.Contains(errorOutput, "contains a virus") || strings.Contains(err.Error(), "contains a virus") {
			return "", fmt.Errorf("%w\nRead: https://AdbAutoPlayer.github.io/AdbAutoPlayer/user-guide/troubleshoot.html#file-contains-a-virus-or-potentially-unwanted-software", err)
		}

		lines := strings.Split(output, "\n")

		if len(lines) > 0 {
			var lastLine string
			for i := len(lines) - 1; i >= 0; i-- {
				lastLine = strings.TrimSpace(lines[i])
				if lastLine != "" {
					break
				}
			}

			var logMessage ipc.LogMessage
			if err = json.Unmarshal([]byte(lastLine), &logMessage); err == nil {
				return "", err
			}
		}

		if pm.IsDev {
			return "", fmt.Errorf("failed to execute '%s': %w\nStdout: %s\nStderr: %s", binaryPath, err, output, errorOutput)
		}

		logger.Get().Debugf("failed to execute '%s': %v\nStdout: %s\nStderr: %s", binaryPath, err, output, errorOutput)

		return "", fmt.Errorf("failed to execute command: %w\nStderr: %s", err, errorOutput)
	}

	return stdout.String(), nil
}

func (pm *Manager) processEnded() {
	pm.running = nil
	app.Emit(event_names.AddSummaryToLog)
}
