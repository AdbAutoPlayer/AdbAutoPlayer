package updater

import (
	"archive/zip"
	"context"
	"encoding/json"
	"fmt"
	"github.com/wailsapp/wails/v2/pkg/runtime"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

type UpdateInfo struct {
	Available   bool   `json:"available"`
	Version     string `json:"version"`
	DownloadURL string `json:"downloadURL"`
	Size        int64  `json:"size"`
	Error       string `json:"error,omitempty"`
}

type GitHubRelease struct {
	TagName string `json:"tag_name"`
	Assets  []struct {
		BrowserDownloadURL string `json:"browser_download_url"`
		Size               int64  `json:"size"`
		Name               string `json:"name"`
	} `json:"assets"`
}

type UpdateManager struct {
	ctx              context.Context
	currentVersion   string
	isDev            bool
	progressCallback func(float64)
	processesToKill  []string // List of process names to terminate before update
}

func NewUpdateManager(ctx context.Context, currentVersion string, isDev bool) *UpdateManager {
	return &UpdateManager{
		ctx:             ctx,
		currentVersion:  currentVersion,
		isDev:           isDev,
		processesToKill: []string{"adb_auto_player.exe", "adb.exe"},
	}
}

func (um *UpdateManager) SetProgressCallback(callback func(float64)) {
	um.progressCallback = callback
}

func (um *UpdateManager) CheckForUpdates() UpdateInfo {
	if um.isDev {
		return UpdateInfo{Available: false}
	}

	resp, err := http.Get("https://api.github.com/repos/AdbAutoPlayer/AdbAutoPlayer/releases/latest")
	if err != nil {
		return UpdateInfo{Error: err.Error()}
	}
	defer func() {
		if err = resp.Body.Close(); err != nil {
			runtime.LogErrorf(um.ctx, "resp.Body.Close error: %v", err)
		}
	}()

	var release GitHubRelease
	if err := json.NewDecoder(resp.Body).Decode(&release); err != nil {
		return UpdateInfo{Error: err.Error()}
	}

	if release.TagName != um.currentVersion {
		// Find Windows asset
		var windowsAsset *struct {
			BrowserDownloadURL string `json:"browser_download_url"`
			Size               int64  `json:"size"`
			Name               string `json:"name"`
		}

		for _, asset := range release.Assets {
			if strings.Contains(strings.ToLower(asset.Name), "windows") ||
				strings.Contains(strings.ToLower(asset.Name), "win") {
				windowsAsset = &asset
				break
			}
		}

		if windowsAsset == nil && len(release.Assets) > 0 {
			// Fallback to first asset if no Windows-specific asset found
			windowsAsset = &release.Assets[0]
		}

		if windowsAsset != nil {
			return UpdateInfo{
				Available:   true,
				Version:     release.TagName,
				DownloadURL: windowsAsset.BrowserDownloadURL,
				Size:        windowsAsset.Size,
			}
		}
	}

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

func (um *UpdateManager) downloadFile(url, filepath string) error {
	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer func() {
		if err = resp.Body.Close(); err != nil {
			runtime.LogErrorf(um.ctx, "resp.Body.Close error: %v", err)
		}
	}()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("bad status: %s", resp.Status)
	}

	out, err := os.Create(filepath)
	if err != nil {
		return err
	}
	defer func() {
		if err = out.Close(); err != nil {
			runtime.LogErrorf(um.ctx, "out.Close error: %v", err)
		}
	}()

	// Create a progress reader if callback is set
	var reader io.Reader = resp.Body
	if um.progressCallback != nil && resp.ContentLength > 0 {
		reader = &progressReader{
			reader:   resp.Body,
			total:    resp.ContentLength,
			callback: um.progressCallback,
		}
	}

	_, err = io.Copy(out, reader)
	return err
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
		time.Sleep(3 * time.Second)
	}

	return lastErr
}

func (um *UpdateManager) killProcessByName(name string) error {
	cmd := exec.Command("taskkill", "/F", "/IM", name)
	return cmd.Run()
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
	// Simple cleanup batch that waits for current process to exit, then cleans up
	batchContent := fmt.Sprintf(`@echo off
echo Waiting for application to close...
timeout /t 2 /nobreak >nul

echo Cleaning up old files...
del "%s" >nul 2>&1

echo Starting updated application...
start "" "%s"

echo Update complete.
del "%%~f0" >nul 2>&1
`, oldExePath, currentExe)

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
	time.Sleep(500 * time.Millisecond)

	// Execute the batch script
	cmd := exec.Command("cmd", "/C", batchPath)
	if err := cmd.Start(); err != nil {
		return err
	}

	// Wait a moment then exit the current application
	time.Sleep(1 * time.Second)
	runtime.Quit(um.ctx)
	return nil
}

// progressReader wraps an io.Reader to report download progress
type progressReader struct {
	reader   io.Reader
	total    int64
	current  int64
	callback func(float64)
}

func (pr *progressReader) Read(p []byte) (int, error) {
	n, err := pr.reader.Read(p)
	pr.current += int64(n)

	if pr.callback != nil {
		progress := float64(pr.current) / float64(pr.total) * 100
		pr.callback(progress)
	}

	return n, err
}
