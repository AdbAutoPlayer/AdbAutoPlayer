//go:build windows

package updater

import (
	"adb-auto-player/internal/app"
	"adb-auto-player/internal/logger"
	ipcprocess "adb-auto-player/internal/process"
	"archive/zip"
	"fmt"
	"github.com/shirou/gopsutil/process"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"
)

func (u *UpdateManager) DownloadAndApplyUpdate(downloadURL string) error {
	// Create temp directory for download
	tempDir, err := os.MkdirTemp("", "app-update-*")
	if err != nil {
		return fmt.Errorf("failed to create temp directory: %w", err)
	}
	defer func(path string) {
		if err = os.RemoveAll(path); err != nil {
			logger.Get().Errorf("failed to remove temp directory: %v", err)
		}
	}(tempDir)

	// Download the update file
	zipPath := filepath.Join(tempDir, "update.zip")
	if err = u.downloadFile(downloadURL, zipPath); err != nil {
		return fmt.Errorf("failed to download update: %w", err)
	}

	// Extract the zip file
	extractDir := filepath.Join(tempDir, "extracted")
	if err = u.extractZip(zipPath, extractDir); err != nil {
		return fmt.Errorf("failed to extract update: %w", err)
	}

	// Apply the update
	if err = u.applyUpdate(extractDir); err != nil {
		return fmt.Errorf("failed to apply update: %w", err)
	}

	return nil
}

func (u *UpdateManager) extractZip(src, dest string) error {
	r, err := zip.OpenReader(src)
	if err != nil {
		return err
	}
	defer func() {
		if err = r.Close(); err != nil {
			logger.Get().Errorf("r.Close error: %v", err)
		}
	}()

	if err = os.MkdirAll(dest, 0755); err != nil {
		return err
	}

	for _, f := range r.File {
		rc, err2 := f.Open()
		if err2 != nil {
			return err2
		}

		path := filepath.Join(dest, f.Name)
		if !strings.HasPrefix(path, filepath.Clean(dest)+string(os.PathSeparator)) {
			if err = rc.Close(); err != nil {
				return err
			}
			return fmt.Errorf("invalid file path: %s", f.Name)
		}

		if f.FileInfo().IsDir() {
			if err = os.MkdirAll(path, f.FileInfo().Mode()); err != nil {
				return err
			}
			if err = rc.Close(); err != nil {
				return err
			}
			continue
		}

		if err = os.MkdirAll(filepath.Dir(path), 0755); err != nil {
			return err
		}
		outFile, err2 := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, f.FileInfo().Mode())
		if err2 != nil {
			if err = rc.Close(); err != nil {
				return err
			}
			return err2
		}

		_, err = io.Copy(outFile, rc)
		if err != nil {
			return err
		}
		if err = outFile.Close(); err != nil {
			return err
		}
		if err = rc.Close(); err != nil {
			return err
		}
	}

	return nil
}

func (u *UpdateManager) applyUpdate(extractDir string) error {
	// Get current executable path
	currentExe, err := os.Executable()
	if err != nil {
		return fmt.Errorf("failed to get current executable path: %w", err)
	}

	currentDir := filepath.Dir(currentExe)

	// Shutting down IPC Service again just in case.
	ipcprocess.GetService().Shutdown()

	// Kill specified processes (but not ourselves)
	if err = u.killProcesses(); err != nil {
		logger.Get().Warningf("Failed to kill some processes: %v", err)
	}

	// Find the new executable in the extracted files
	newExePath, err := u.findNewExecutable(extractDir)
	if err != nil {
		return fmt.Errorf("failed to find new executable: %w", err)
	}

	// Step 1: Rename current executable to .old
	oldExePath := currentExe + ".old"
	if err = os.Rename(currentExe, oldExePath); err != nil {
		return fmt.Errorf("failed to rename current executable: %w", err)
	}

	// Step 2: Move new executable to current executable path
	if err = u.moveFile(newExePath, currentExe); err != nil {
		// Restore original executable if move failed
		if err = os.Rename(oldExePath, currentExe); err != nil {
			return fmt.Errorf("failed to rename old executable: %w", err)
		}
		return fmt.Errorf("failed to move new executable: %w", err)
	}

	// Step 3: Copy other files (skip the main exe since we already moved it)
	if err = u.copyOtherFiles(extractDir, currentDir, filepath.Base(currentExe)); err != nil {
		return err
	}

	// Step 4: Create cleanup batch script and restart
	batchScript, err := u.createCleanupBatch(oldExePath, currentExe)
	if err != nil {
		return err
	}
	go func() {
		err = u.executeRestartBatch(batchScript)
		if err != nil {
			logger.Get().Errorf("Failed to execute restart batch: %v", err)
		}
	}()

	return nil
}

func (u *UpdateManager) copyFile(src, dst string) error {
	sourceFile, err := os.Open(src)
	if err != nil {
		return err
	}
	defer func() {
		if err = sourceFile.Close(); err != nil {
			logger.Get().Errorf("sourceFile.Close error: %v", err)
		}
	}()

	destFile, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer func() {
		if err = destFile.Close(); err != nil {
			logger.Get().Errorf("destFile.Close error: %v", err)
		}
	}()

	_, err = io.Copy(destFile, sourceFile)
	if err != nil {
		return err
	}

	// Copy file permissions
	sourceInfo, err := os.Stat(src)
	if err != nil {
		return err
	}

	return os.Chmod(dst, sourceInfo.Mode())
}

func (u *UpdateManager) killProcesses() error {
	var lastErr error

	for _, processName := range u.processesToKill {
		if err := u.killProcessByName(processName); err != nil {
			lastErr = err
			logger.Get().Warningf("Failed to kill process %s: %v", processName, err)
		}
	}
	// Wait for processes to be killed
	time.Sleep(5 * time.Second)

	return lastErr
}

func (u *UpdateManager) killProcessByName(name string) error {
	currentExe, err := os.Executable()
	if err != nil {
		return err
	}
	updaterDir := filepath.Dir(currentExe)

	procs, err := process.Processes()
	if err != nil {
		return err
	}

	var targetProcesses []*process.Process
	var lastErr error

	expectedPath := filepath.Join(updaterDir, "binaries", name)

	for _, p := range procs {
		exe, err2 := p.Exe()
		if err2 != nil {
			continue
		}

		// Case-insensitive match
		if strings.EqualFold(exe, expectedPath) {
			targetProcesses = append(targetProcesses, p)
		}
	}

	// Kill each target process and its children
	for _, proc := range targetProcesses {
		if err = u.killProcessTree(proc); err != nil {
			lastErr = err
		}
	}

	return lastErr
}

// killProcessTree kills a process and all its descendants using gopsutil's Children method
func (u *UpdateManager) killProcessTree(proc *process.Process) error {
	var lastErr error

	children, err := proc.Children()
	if err != nil {
		logger.Get().Warningf("Could not get children for process PID %d: %v", proc.Pid, err)
	}

	for _, child := range children {
		exe, err2 := child.Exe()
		if err2 != nil {
			exe = "unknown"
		}

		if err = child.Kill(); err != nil {
			lastErr = err
			logger.Get().Errorf("Failed to kill child process PID %d at %s: %v", child.Pid, exe, err)
		} else {
			logger.Get().Infof("Killed child process PID %d at %s", child.Pid, exe)
		}
	}

	exe, err := proc.Exe()
	if err != nil {
		exe = "unknown"
	}

	if err = proc.Kill(); err != nil {
		lastErr = err
		logger.Get().Errorf("Failed to kill process PID %d at %s: %v", proc.Pid, exe, err)
	} else {
		logger.Get().Infof("Killed process PID %d at %s", proc.Pid, exe)

	}

	return lastErr
}

func (u *UpdateManager) findNewExecutable(extractDir string) (string, error) {
	var exePath string

	err := filepath.Walk(extractDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		if !info.IsDir() && strings.HasSuffix(strings.ToLower(info.Name()), ".exe") {
			// Prefer exe files that match common patterns
			name := strings.ToLower(info.Name())
			if strings.Contains(name, "adbautoplayer") || strings.Contains(name, "main") {
				exePath = path
				return filepath.SkipDir // Found our target, stop searching
			}

			// Fallback to any exe file
			if exePath == "" {
				exePath = path
			}
		}

		return nil
	})

	if err != nil {
		return "", err
	}

	if exePath == "" {
		return "", fmt.Errorf("no executable file found in update")
	}

	return exePath, nil
}

func (u *UpdateManager) moveFile(src, dst string) error {
	// Try rename first (fastest if on same drive)
	if err := os.Rename(src, dst); err == nil {
		return nil
	}

	// Fallback to copy + delete
	if err := u.copyFile(src, dst); err != nil {
		return err
	}

	return os.Remove(src)
}

func (u *UpdateManager) copyOtherFiles(extractDir, currentDir, skipFileName string) error {
	return filepath.Walk(extractDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		// Skip the main executable since we already moved it
		if !info.IsDir() && strings.EqualFold(info.Name(), skipFileName) {
			return nil
		}

		relPath, err := filepath.Rel(extractDir, path)
		if err != nil {
			return err
		}

		destPath := filepath.Join(currentDir, relPath)

		if info.IsDir() {
			return os.MkdirAll(destPath, info.Mode())
		}

		return u.copyFile(path, destPath)
	})
}

func (u *UpdateManager) createCleanupBatch(oldExePath, currentExe string) (string, error) {
	// Get the current process name for the batch script to wait for it to exit
	currentExeName := filepath.Base(currentExe)

	// Enhanced cleanup batch that properly waits for process to exit
	batchContent := fmt.Sprintf(`@echo off
echo Waiting for application to close...

REM Wait for the process to actually exit (up to 30 seconds)
set /a counter=0
:waitloop
tasklist /FI "IMAGENAME eq %s" 2>NUL | find /I "%s" >NUL
if not errorlevel 1 (
    set /a counter+=1
    if %%counter%% lss 30 (
        timeout /t 1 /nobreak >nul
        goto waitloop
    ) else (
        echo Warning: Process still running after 30 seconds
    )
)

echo Process has exited, cleaning up old files...
REM Try multiple times to delete the old file in case of file locks
set /a delete_counter=0
:deleteloop
if exist "%s" (
    del "%s" >nul 2>&1
    if exist "%s" (
        set /a delete_counter+=1
        if %%delete_counter%% lss 5 (
            timeout /t 1 /nobreak >nul
            goto deleteloop
        ) else (
            echo Warning: Could not delete old executable after 5 attempts
        )
    ) else (
        echo Old executable cleaned up successfully
    )
) else (
    echo Old executable already removed
)

echo Starting updated application...
start "" "%s"

echo Update complete.
REM Clean up this batch file
(goto) 2>nul & del "%%~f0"
`, currentExeName, currentExeName, oldExePath, oldExePath, oldExePath, currentExe)

	// Write batch script to temp file
	batchPath := filepath.Join(os.TempDir(), "cleanup_"+fmt.Sprintf("%d", time.Now().Unix())+".bat")
	err := os.WriteFile(batchPath, []byte(batchContent), 0644)
	if err != nil {
		return "", err
	}

	return batchPath, nil
}

func (u *UpdateManager) executeRestartBatch(batchPath string) error {
	// Wait a moment to ensure the batch file is written
	time.Sleep(1 * time.Second)

	// Execute the batch script in a detached process
	cmd := exec.Command("cmd", "/C", batchPath)
	cmd.SysProcAttr = &syscall.SysProcAttr{
		CreationFlags: syscall.CREATE_NEW_PROCESS_GROUP,
	}

	if err := cmd.Start(); err != nil {
		return err
	}

	// Give the batch script a moment to start, then exit
	time.Sleep(1 * time.Second)
	app.Quit()
	return nil
}
