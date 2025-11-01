//go:build !windows

package process

import (
	"adb-auto-player/internal/logger"
	"fmt"

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
