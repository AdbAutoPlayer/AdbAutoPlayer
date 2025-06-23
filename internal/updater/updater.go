package updater

import (
	"context"
	"fmt"
	"github.com/Masterminds/semver"
	"github.com/google/go-github/v72/github"
	"github.com/wailsapp/wails/v2/pkg/runtime"
	"io"
	"net/http"
	"os"
	"strings"
)

type UpdateInfo struct {
	Available   bool   `json:"available"`
	Version     string `json:"version"`
	DownloadURL string `json:"downloadURL"`
	Size        int64  `json:"size"`
	Error       string `json:"error,omitempty"`
	AutoUpdate  bool   `json:"autoUpdate"`
}

type Changelog struct {
	Body    string `json:"body"`
	Version string `json:"version"`
}

type UpdateManager struct {
	ctx              context.Context
	currentVersion   string
	isDev            bool
	progressCallback func(float64)
	processesToKill  []string // List of process names to terminate before update
	githubClient     *github.Client
	owner            string
	repo             string
	latestRelease    *github.RepositoryRelease
	releasesBetween  []*github.RepositoryRelease // Releases between current and latest
}

func NewUpdateManager(ctx context.Context, currentVersion string, isDev bool) *UpdateManager {
	return &UpdateManager{
		ctx:             ctx,
		currentVersion:  currentVersion,
		isDev:           isDev,
		processesToKill: []string{"adb.exe", "adb_auto_player.exe", "tesseract.exe"},
		githubClient:    github.NewClient(nil), // nil http.Client means no authentication
		owner:           "AdbAutoPlayer",
		repo:            "AdbAutoPlayer",
	}
}

func (um *UpdateManager) SetProgressCallback(callback func(float64)) {
	um.progressCallback = callback
}

// GetReleasesBetween returns the cached releases between current and latest
func (um *UpdateManager) GetReleasesBetween() []*github.RepositoryRelease {
	return um.releasesBetween
}

// GetChangelog combines changelog from latest release and releases in between
func (um *UpdateManager) GetChangelogs() []Changelog {
	var changelogs []Changelog

	if um.latestRelease != nil && um.latestRelease.Body != nil {
		changelogs = append(changelogs, Changelog{
			Body:    *um.latestRelease.Body,
			Version: *um.latestRelease.TagName,
		})
	}

	for _, release := range um.releasesBetween {
		if release != nil && release.Body != nil {
			changelogs = append(changelogs, Changelog{
				Body:    *release.Body,
				Version: *release.TagName,
			})
		}
	}

	return changelogs
}

// getLatestReleaseIncludingPrerelease gets the latest release including pre-releases
func (um *UpdateManager) getLatestReleaseIncludingPrerelease() (*github.RepositoryRelease, error) {
	releases, _, err := um.githubClient.Repositories.ListReleases(um.ctx, um.owner, um.repo, &github.ListOptions{
		PerPage: 30, // Get first 30 releases to find the latest
	})
	if err != nil {
		return nil, fmt.Errorf("failed to list releases: %w", err)
	}
	if len(releases) == 0 {
		return nil, fmt.Errorf("no releases found")
	}

	// Find the first release with usable assets
	for _, release := range releases {
		if release.TagName != nil && len(release.Assets) > 0 {
			hasUsableAsset := false
			for _, asset := range release.Assets {
				if asset.Name != nil && strings.HasSuffix(strings.ToLower(*asset.Name), "_windows.zip") {
					hasUsableAsset = true
					break
				}
			}

			if hasUsableAsset {
				return release, nil
			}
		}
	}

	// Fallback to first release if no specific Windows asset found
	return releases[0], nil
}

// getReleasesBetweenTags returns all releases between two semver tags
func (um *UpdateManager) getReleasesBetweenTags(startTag, endTag string) ([]*github.RepositoryRelease, error) {
	// Parse the version constraints
	startVer, err := semver.NewVersion(startTag)
	if err != nil {
		return nil, fmt.Errorf("invalid start tag: %w", err)
	}

	endVer, err := semver.NewVersion(endTag)
	if err != nil {
		return nil, fmt.Errorf("invalid end tag: %w", err)
	}

	// Get all releases
	releases, _, err := um.githubClient.Repositories.ListReleases(um.ctx, um.owner, um.repo, &github.ListOptions{
		PerPage: 100, // Maximum allowed by GitHub API
	})
	if err != nil {
		return nil, fmt.Errorf("failed to list releases: %w", err)
	}

	var filteredReleases []*github.RepositoryRelease

	for _, release := range releases {
		if release.TagName == nil {
			continue
		}

		// Parse the release version
		releaseVer, err := semver.NewVersion(*release.TagName)
		if err != nil {
			continue // skip non-semver tags
		}

		// Check if the release is within our range (exclusive of start and end)
		if releaseVer.GreaterThan(startVer) && releaseVer.LessThan(endVer) {
			filteredReleases = append(filteredReleases, release)
		}
	}

	return filteredReleases, nil
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
