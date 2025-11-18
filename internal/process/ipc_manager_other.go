//go:build !windows

package process

import (
	"adb-auto-player/internal/logger"
	"fmt"
	"os/exec"
	"runtime"

	"github.com/shirou/gopsutil/v4/process"
)

// startServer starts the FastAPI server process.
func (pm *IPCManager) startServer() error {
	cmd, err := getServerStartCommand(pm.isDev, pm.pythonBinaryPath, "--server")
	if err != nil {
		return fmt.Errorf("failed to get server command: %w", err)
	}

	if err = cmd.Start(); err != nil {
		return fmt.Errorf("failed to start server: %w", err)
	}
	logger.Get().Debugf("Started server with PID: %d", cmd.Process.Pid)

	proc, err := process.NewProcess(int32(cmd.Process.Pid))
	if err != nil {
		return fmt.Errorf("failed to create process handle: %w", err)
	}
	pm.serverProcess = proc

	return nil
}

// shutdownSystem shuts down the system (macOS or Linux).
func shutdownSystem() error {
	if runtime.GOOS == "darwin" {
		// macOS: Use osascript to shutdown (doesn't require sudo)
		cmd := exec.Command("osascript", "-e", "tell app \"System Events\" to shut down")
		if err := cmd.Run(); err != nil {
			return fmt.Errorf("failed to shutdown macOS system: %w", err)
		}
		logger.Get().Infof("System shutdown initiated")
		return nil
	}

	// Linux: Try systemctl first (systemd), then fall back to shutdown/poweroff
	// Note: These may require sudo privileges
	commands := [][]string{
		{"systemctl", "poweroff"},
		{"shutdown", "-h", "now"},
		{"poweroff"},
	}

	var lastErr error
	for _, args := range commands {
		cmd := exec.Command(args[0], args[1:]...)
		if err := cmd.Run(); err != nil {
			lastErr = err
			continue
		}
		logger.Get().Infof("System shutdown initiated using: %s", args[0])
		return nil
	}

	return fmt.Errorf("failed to shutdown Linux system: %w (note: this may require sudo privileges)", lastErr)
}
