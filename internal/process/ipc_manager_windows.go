package process

import (
	"adb-auto-player/internal/logger"
	"fmt"
	"unsafe"

	"github.com/shirou/gopsutil/v4/process"
	"golang.org/x/sys/windows"
)

// startServer starts the FastAPI server process.
func (pm *IPCManager) startServer() error {
	cmd, err := getServerStartCommand(pm.isDev, pm.pythonBinaryPath, "--server")
	if err != nil {
		return fmt.Errorf("failed to get server command: %w", err)
	}

	// Create Job Object so child dies with parent
	job, err := windows.CreateJobObject(nil, nil)
	if err != nil {
		return fmt.Errorf("failed to create job object: %w", err)
	}
	var info windows.JOBOBJECT_EXTENDED_LIMIT_INFORMATION
	info.BasicLimitInformation.LimitFlags = windows.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
	if _, jobErr := windows.SetInformationJobObject(
		job,
		windows.JobObjectExtendedLimitInformation,
		uintptr(unsafe.Pointer(&info)),
		uint32(unsafe.Sizeof(info)),
	); jobErr != nil {
		return fmt.Errorf("failed to set job info: %w", jobErr)
	}

	// Start the FastAPI server
	if err = cmd.Start(); err != nil {
		return fmt.Errorf("failed to start server: %w", err)
	}
	logger.Get().Debugf("Started server with PID: %d", cmd.Process.Pid)

	// Open process handle for AssignProcessToJobObject
	const processAllAccess = windows.PROCESS_ALL_ACCESS
	hProcess, err := windows.OpenProcess(processAllAccess, false, uint32(cmd.Process.Pid))
	if err != nil {
		return fmt.Errorf("failed to open process handle: %w", err)
	}
	defer func(handle windows.Handle) {
		if err = windows.CloseHandle(handle); err != nil {
			logger.Get().Errorf("failed to close handle: %v", err)
		}
	}(hProcess)

	if err = windows.AssignProcessToJobObject(job, hProcess); err != nil {
		return fmt.Errorf("failed to assign process to job: %w", err)
	}

	// Store the process info
	proc, err := process.NewProcess(int32(cmd.Process.Pid))
	if err != nil {
		return fmt.Errorf("failed to create process handle: %w", err)
	}
	pm.serverProcess = proc

	return nil
}
