package internal

import (
	"adb-auto-player/internal/ipc"
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/shirou/gopsutil/process"
	"github.com/wailsapp/wails/v2/pkg/runtime"
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
	ctx            context.Context
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

func (pm *Manager) SetContext(ctx context.Context) {
	pm.ctx = ctx
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
	ipc.GetFrontendLogger().Debugf("Started process with PID: %d", cmd.Process.Pid)

	originalLogLevel := ipc.GetFrontendLogger().LogLevel
	if len(logLevel) > 0 {
		ipc.GetFrontendLogger().LogLevel = logLevel[0]
	}

	proc, err := process.NewProcess(int32(cmd.Process.Pid))
	if err != nil {
		return fmt.Errorf("failed to create process handle: %w", err)
	}
	pm.running = proc

	debugDir := "debug"
	if err = os.MkdirAll(debugDir, 0755); err != nil {
		ipc.GetFrontendLogger().Errorf("Failed to create debug directory: %v", err)
	}

	timestamp := time.Now().Format("20060102_150405")
	sanitizedArgs := strings.Join(args, "_")
	sanitizedArgs = regexp.MustCompile(`[^a-zA-Z0-9_-]`).ReplaceAllString(sanitizedArgs, "")
	logFileName := fmt.Sprintf("%s_%s.log", timestamp, sanitizedArgs)
	logFilePath := filepath.Join(debugDir, logFileName)

	logFile, err := os.Create(logFilePath)
	if err != nil {
		ipc.GetFrontendLogger().Errorf("Failed to create log file: %v", err)
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
				if err := os.Remove(files[i]); err != nil {
					ipc.GetFrontendLogger().Errorf("Failed to delete old log file %s: %v", files[i], err)
				}
			}
		}
	}

	go func() {
		scanner := bufio.NewScanner(stdoutPipe)
		scanner.Buffer(make([]byte, 4096), 1024*1024)

		for scanner.Scan() {
			line := scanner.Text()
			if logFile != nil {
				if _, err = fmt.Fprintln(logFile, line); err != nil {
					ipc.GetFrontendLogger().Errorf("Failed to write to log file: %v", err)
				}
			}

			var summaryMessage ipc.Summary
			if err = json.Unmarshal([]byte(line), &summaryMessage); err == nil {
				if summaryMessage.SummaryMessage != "" {
					runtime.EventsEmit(pm.ctx, "summary-message", summaryMessage)
					continue
				}
			}

			var logMessage ipc.LogMessage
			if err = json.Unmarshal([]byte(line), &logMessage); err == nil {
				// fmt.Printf("%+v\n", logMessage)
				ipc.GetFrontendLogger().LogMessage(logMessage)
				continue
			}

			ipc.GetFrontendLogger().Errorf("Failed to parse JSON message: %v", err)
		}

		if err = scanner.Err(); err != nil {
			if !strings.Contains(err.Error(), "file already closed") {
				ipc.GetFrontendLogger().Errorf("Error while reading stdout: %v", err)
			}
		}
	}()

	go func() {
		_, err = cmd.Process.Wait()
		if err != nil {
			ipc.GetFrontendLogger().Errorf("Process ended with error: %v", err)
		}

		pm.mutex.Lock()
		ipc.GetFrontendLogger().LogLevel = originalLogLevel
		pm.processEnded()
		pm.mutex.Unlock()
	}()

	return nil
}

func (pm *Manager) KillProcess() {
	pm.mutex.Lock()
	defer pm.mutex.Unlock()

	if pm.running == nil || !pm.isProcessRunning() {
		return
	}

	killProcessTree(pm.running)

	runtime.LogWarning(pm.ctx, "Stopping")
	time.Sleep(2 * time.Second)
	pm.processEnded()
}

func killProcessTree(p *process.Process) {
	children, err := p.Children()
	if err != nil && !errors.Is(err, process.ErrorNoChildren) {
		ipc.GetFrontendLogger().Errorf("Failed to get children of process %d: %v", p.Pid, err)
	}

	for _, child := range children {
		killProcessTree(child) // recurse
	}

	if err = p.Kill(); err != nil {
		if strings.Contains(err.Error(), "no such process") {
			ipc.GetFrontendLogger().Debugf("Process %d already exited", p.Pid)
		} else {
			ipc.GetFrontendLogger().Errorf("Failed to kill process %d: %v", p.Pid, err)
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

		fmt.Printf("dev python dir: %s\n", name)

		uvPath, err := exec.LookPath("uv")
		if err != nil {
			return nil, fmt.Errorf("uv not found in PATH: %w", err)
		}

		fmt.Printf("uv path: %s\n", uvPath)

		cmd := exec.Command(uvPath, append([]string{"run", "adb-auto-player"}, args...)...)
		fmt.Println("cmd.Args: ", cmd.Args)

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
		fmt.Println("lines:", lines)

		if len(lines) > 0 {
			var lastLine string
			for i := len(lines) - 1; i >= 0; i-- {
				lastLine = strings.TrimSpace(lines[i])
				if lastLine != "" {
					break
				}
			}
			fmt.Println("lastLine:", lastLine)

			var logMessage ipc.LogMessage
			if err = json.Unmarshal([]byte(lastLine), &logMessage); err == nil {
				fmt.Println("logMessage.Message:", logMessage.Message)
				return "", fmt.Errorf(logMessage.Message)
			}
		}

		if pm.IsDev {
			return "", fmt.Errorf("failed to execute '%s': %w\nStdout: %s\nStderr: %s", binaryPath, err, output, errorOutput)
		}
		return "", fmt.Errorf("failed to execute command: %w\nStderr: %s", err, errorOutput)
	}

	return stdout.String(), nil
}

func (pm *Manager) processEnded() {
	pm.running = nil
	runtime.EventsEmit(pm.ctx, "add-summary-to-log")
}
