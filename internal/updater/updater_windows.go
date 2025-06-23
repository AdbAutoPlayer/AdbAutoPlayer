//go:build windows

package updater

import (
	"adb-auto-player/internal"
	"archive/zip"
	"fmt"
	"github.com/Masterminds/semver"
	"github.com/google/go-github/v72/github"
	"github.com/shirou/gopsutil/process"
	"github.com/wailsapp/wails/v2/pkg/runtime"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"
)

func (um *UpdateManager) CheckForUpdates(autoUpdate bool, enableAlphaUpdates bool) UpdateInfo {
	if um.isDev {
		runtime.LogDebug(um.ctx, "Updater disabled for dev.")
		return UpdateInfo{Available: false}
	}

	currentVer, err1 := semver.NewVersion(um.currentVersion)
	if err1 != nil {
		return UpdateInfo{Error: fmt.Sprintf("current version parse error: %v", err1)}
	}

	isCurrentPrerelease := currentVer.Prerelease() != ""

	var latestRelease *github.RepositoryRelease
	var err error

	if enableAlphaUpdates || isCurrentPrerelease {
		// Get all releases to include pre-releases/alphas
		latestRelease, err = um.getLatestReleaseIncludingPrerelease()
	} else {
		// Get only the latest stable release
		latestRelease, _, err = um.githubClient.Repositories.GetLatestRelease(um.ctx, um.owner, um.repo)
		if err != nil {
			return UpdateInfo{Error: fmt.Sprintf("failed to get latest release: %v", err)}
		}
	}

	if err != nil {
		return UpdateInfo{Error: err.Error()}
	}

	if latestRelease == nil || latestRelease.TagName == nil {
		return UpdateInfo{Available: false}
	}

	um.latestRelease = latestRelease

	latestVer, err2 := semver.NewVersion(*latestRelease.TagName)
	if err2 != nil {
		return UpdateInfo{Error: fmt.Sprintf("latest version parse error: %v", err2)}
	}

	if latestVer.GreaterThan(currentVer) {
		// Get releases between current and latest for changelog
		releasesBetween, err := um.getReleasesBetweenTags(um.currentVersion, *latestRelease.TagName)
		fmt.Printf("Number of releases between tags: %d\n", len(releasesBetween))
		if err != nil {
			runtime.LogWarningf(um.ctx, "Failed to get releases between versions: %v", err)
		} else {
			um.releasesBetween = releasesBetween
		}

		// Find Windows asset
		var windowsAsset *github.ReleaseAsset
		for _, asset := range latestRelease.Assets {
			if asset.Name != nil &&
				(strings.Contains(strings.ToLower(*asset.Name), "windows") ||
					strings.Contains(strings.ToLower(*asset.Name), "win")) {
				windowsAsset = asset
				break
			}
		}

		if windowsAsset == nil && len(latestRelease.Assets) > 0 {
			// Fallback to first asset if no Windows-specific asset found
			windowsAsset = latestRelease.Assets[0]
		}

		if windowsAsset != nil && windowsAsset.BrowserDownloadURL != nil {
			size := int64(0)
			if windowsAsset.Size != nil {
				size = int64(*windowsAsset.Size)
			}

			return UpdateInfo{
				Available:   true,
				Version:     *latestRelease.TagName,
				DownloadURL: *windowsAsset.BrowserDownloadURL,
				Size:        size,
				AutoUpdate:  autoUpdate,
			}
		}
	}

	runtime.LogDebug(um.ctx, "No updates available.")
	return UpdateInfo{Available: false}
}

func (um *UpdateManager) DownloadAndApplyUpdate(downloadURL string) error {
	// Create temp directory for download
	tempDir, err := os.MkdirTemp("", "app-update-*")
	if err != nil {
		return fmt.Errorf("failed to create temp directory: %w", err)
	}
	defer func(path string) {
		if err = os.RemoveAll(path); err != nil {
			runtime.LogErrorf(um.ctx, "failed to remove temp directory: %v", err)
		}
	}(tempDir)

	// Download the update file
	zipPath := filepath.Join(tempDir, "update.zip")
	if err = um.downloadFile(downloadURL, zipPath); err != nil {
		return fmt.Errorf("failed to download update: %w", err)
	}

	// Extract the zip file
	extractDir := filepath.Join(tempDir, "extracted")
	if err = um.extractZip(zipPath, extractDir); err != nil {
		return fmt.Errorf("failed to extract update: %w", err)
	}

	// Apply the update
	if err = um.applyUpdate(extractDir); err != nil {
		return fmt.Errorf("failed to apply update: %w", err)
	}

	return nil
}

func (um *UpdateManager) extractZip(src, dest string) error {
	r, err := zip.OpenReader(src)
	if err != nil {
		return err
	}
	defer func() {
		if err = r.Close(); err != nil {
			runtime.LogErrorf(um.ctx, "r.Close error: %v", err)
		}
	}()

	if err = os.MkdirAll(dest, 0755); err != nil {
		return err
	}

	for _, f := range r.File {
		rc, err := f.Open()
		if err != nil {
			return err
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
		outFile, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, f.FileInfo().Mode())
		if err != nil {
			if err = rc.Close(); err != nil {
				return err
			}
			return err
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

func (um *UpdateManager) applyUpdate(extractDir string) error {
	internal.GetProcessManager().KillProcess()

	// Get current executable path
	currentExe, err := os.Executable()
	if err != nil {
		return fmt.Errorf("failed to get current executable path: %w", err)
	}

	currentDir := filepath.Dir(currentExe)

	// Kill specified processes (but not ourselves)
	if err := um.killProcesses(); err != nil {
		runtime.LogWarningf(um.ctx, "Failed to kill some processes: %v", err)
	}

	// Find the new executable in the extracted files
	newExePath, err := um.findNewExecutable(extractDir)
	if err != nil {
		return fmt.Errorf("failed to find new executable: %w", err)
	}

	// Step 1: Rename current executable to .old
	oldExePath := currentExe + ".old"
	if err = os.Rename(currentExe, oldExePath); err != nil {
		return fmt.Errorf("failed to rename current executable: %w", err)
	}

	// Step 2: Move new executable to current executable path
	if err = um.moveFile(newExePath, currentExe); err != nil {
		// Restore original executable if move failed
		if err = os.Rename(oldExePath, currentExe); err != nil {
			return fmt.Errorf("failed to rename old executable: %w", err)
		}
		return fmt.Errorf("failed to move new executable: %w", err)
	}

	// Step 3: Copy other files (skip the main exe since we already moved it)
	if err = um.copyOtherFiles(extractDir, currentDir, filepath.Base(currentExe)); err != nil {
		return err
	}

	// Step 4: Create cleanup batch script and restart
	batchScript, err := um.createCleanupBatch(oldExePath, currentExe)
	if err != nil {
		return err
	}
	go func() {
		err = um.executeRestartBatch(batchScript)
		if err != nil {
			runtime.LogErrorf(um.ctx, "Failed to execute restart batch: %v", err)
		}
	}()

	return nil
}

func (um *UpdateManager) copyFile(src, dst string) error {
	sourceFile, err := os.Open(src)
	if err != nil {
		return err
	}
	defer func() {
		if err = sourceFile.Close(); err != nil {
			runtime.LogErrorf(um.ctx, "sourceFile.Close error: %v", err)
		}
	}()

	destFile, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer func() {
		if err = destFile.Close(); err != nil {
			runtime.LogErrorf(um.ctx, "destFile.Close error: %v", err)
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

func (um *UpdateManager) killProcesses() error {
	var lastErr error

	for _, processName := range um.processesToKill {
		if err := um.killProcessByName(processName); err != nil {
			lastErr = err
			runtime.LogWarningf(um.ctx, "Failed to kill process %s: %v", processName, err)
		}
	}
	// Wait for processes to be killed
	time.Sleep(5 * time.Second)

	return lastErr
}

func (um *UpdateManager) killProcessByName(name string) error {
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
		exe, err := p.Exe()
		if err != nil {
			continue
		}

		// Case-insensitive match
		if strings.EqualFold(exe, expectedPath) {
			targetProcesses = append(targetProcesses, p)
		}
	}

	// Kill each target process and its children
	for _, proc := range targetProcesses {
		if err = um.killProcessTree(proc); err != nil {
			lastErr = err
		}
	}

	return lastErr
}

// killProcessTree kills a process and all its descendants using gopsutil's Children method
func (um *UpdateManager) killProcessTree(proc *process.Process) error {
	var lastErr error

	children, err := proc.Children()
	if err != nil {
		runtime.LogWarningf(um.ctx, "Could not get children for process PID %d: %v", proc.Pid, err)
	}

	for _, child := range children {
		exe, err := child.Exe()
		if err != nil {
			exe = "unknown"
		}

		if err = child.Kill(); err != nil {
			lastErr = err
			runtime.LogErrorf(um.ctx, "Failed to kill child process PID %d at %s: %v", child.Pid, exe, err)
		} else {
			runtime.LogInfof(um.ctx, "Killed child process PID %d at %s", child.Pid, exe)
		}
	}

	exe, err := proc.Exe()
	if err != nil {
		exe = "unknown"
	}

	if err = proc.Kill(); err != nil {
		lastErr = err
		runtime.LogErrorf(um.ctx, "Failed to kill process PID %d at %s: %v", proc.Pid, exe, err)
	} else {
		runtime.LogInfof(um.ctx, "Killed process PID %d at %s", proc.Pid, exe)
	}

	return lastErr
}

func (um *UpdateManager) findNewExecutable(extractDir string) (string, error) {
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

func (um *UpdateManager) moveFile(src, dst string) error {
	// Try rename first (fastest if on same drive)
	if err := os.Rename(src, dst); err == nil {
		return nil
	}

	// Fallback to copy + delete
	if err := um.copyFile(src, dst); err != nil {
		return err
	}

	return os.Remove(src)
}

func (um *UpdateManager) copyOtherFiles(extractDir, currentDir, skipFileName string) error {
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

		return um.copyFile(path, destPath)
	})
}

func (um *UpdateManager) createCleanupBatch(oldExePath, currentExe string) (string, error) {
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

func (um *UpdateManager) executeRestartBatch(batchPath string) error {
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
	runtime.Quit(um.ctx)
	return nil
}
