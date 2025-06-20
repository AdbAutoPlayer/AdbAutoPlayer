package updater

import (
	"context"
	"fmt"
	"github.com/wailsapp/wails/v2/pkg/runtime"
	"io"
	"net/http"
	"os"
)

type UpdateInfo struct {
	Available   bool   `json:"available"`
	Version     string `json:"version"`
	DownloadURL string `json:"downloadURL"`
	Size        int64  `json:"size"`
	Error       string `json:"error,omitempty"`
	AutoUpdate  bool   `json:"autoUpdate"`
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
		processesToKill: []string{"adb.exe", "adb_auto_player.exe", "tesseract.exe"},
	}
}

func (um *UpdateManager) SetProgressCallback(callback func(float64)) {
	um.progressCallback = callback
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
