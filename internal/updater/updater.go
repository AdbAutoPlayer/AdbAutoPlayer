package updater

import (
	"archive/zip"
	"context"
	"fmt"
	"github.com/wailsapp/wails/v2/pkg/runtime"
	"io"
	"os"
	"path/filepath"
	"strings"
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

func Unzip(ctx context.Context, src, dest string) error {
	r, err := zip.OpenReader(src)
	if err != nil {
		return err
	}
	defer func() {
		if cerr := r.Close(); cerr != nil {
			// Replace runtime.LogErrorf with your actual logging method
			runtime.LogErrorf(ctx, "zip.Reader.Close error: %v", cerr)
		}
	}()

	// Make sure destination exists
	if err := os.MkdirAll(dest, 0755); err != nil {
		return err
	}

	for _, f := range r.File {
		rc, err := f.Open()
		if err != nil {
			return err
		}
		defer func(rc io.ReadCloser) {
			if cerr := rc.Close(); cerr != nil {
				runtime.LogErrorf(ctx, "file.Reader.Close error: %v", cerr)
			}
		}(rc)

		path := filepath.Join(dest, f.Name)

		// Check for directory traversal
		if !strings.HasPrefix(path, filepath.Clean(dest)+string(os.PathSeparator)) {
			return fmt.Errorf("invalid file path: %s", f.Name)
		}

		if f.FileInfo().IsDir() {
			if err := os.MkdirAll(path, f.FileInfo().Mode()); err != nil {
				return err
			}
		} else {
			// Create directory if it doesn't exist
			if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
				return err
			}

			outFile, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, f.FileInfo().Mode())
			if err != nil {
				return err
			}
			defer func(outFile *os.File) {
				if cerr := outFile.Close(); cerr != nil {
					runtime.LogErrorf(ctx, "outFile.Close error: %v", cerr)
				}
			}(outFile)

			if _, err = io.Copy(outFile, rc); err != nil {
				return err
			}
		}
		// no explicit rc.Close() here, deferred above
	}

	return nil
}
