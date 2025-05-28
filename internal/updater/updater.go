package updater

import "context"

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

func (um *UpdateManager) SetProgressCallback(callback func(float64)) {
	um.progressCallback = callback
}
