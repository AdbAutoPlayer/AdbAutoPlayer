package updater

import (
	"adb-auto-player/internal/logger"
	"context"
	"fmt"
	"github.com/Masterminds/semver"
	"github.com/google/go-github/v72/github"
	"github.com/wailsapp/wails/v3/pkg/application"
	"io"
	"net/http"
	"os"
	"runtime"
	"strings"
)

type UpdateInfo struct {
	Available        bool   `json:"available"`
	Version          string `json:"version"`
	ReleaseURL       string `json:"releaseURL"`
	DownloadURL      string `json:"downloadURL"`
	Size             int64  `json:"size"`
	AutoUpdate       bool   `json:"autoUpdate"`
	Disabled         bool   `json:"disabled"`
	RedirectToGitHub bool   `json:"redirectToGitHub"`
}

type Changelog struct {
	Body    string `json:"body"`
	Version string `json:"version"`
}

type UpdateManager struct {
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

func NewUpdateManager(currentVersion string, isDev bool) UpdateManager {
	return UpdateManager{
		currentVersion:  currentVersion,
		isDev:           isDev,
		processesToKill: []string{"adb.exe", "adb_auto_player.exe", "tesseract.exe"},
		githubClient:    github.NewClient(nil), // nil http.Client means no authentication
		owner:           "AdbAutoPlayer",
		repo:            "AdbAutoPlayer",
	}
}

func (u *UpdateManager) CheckForUpdates(autoUpdate bool, checkPrerelease bool) (UpdateInfo, error) {
	if u.isDev {
		/* UI Testing
		return UpdateInfo{
			Available:   true,
			Version:     "1.0.0",
			DownloadURL: "example.com",
			Size:        1,
			AutoUpdate:  false,
		}, nil
		*/
		return UpdateInfo{Available: false}, nil
	}

	currentVer, err := semver.NewVersion(u.currentVersion)
	if err != nil {
		return UpdateInfo{}, fmt.Errorf("failed to parse current version: %w", err)
	}

	latestRelease, err := u.GetLatestRelease(currentVer.Prerelease() != "" || checkPrerelease)
	if err != nil {
		return UpdateInfo{}, err
	}

	if latestRelease == nil || latestRelease.TagName == nil {
		return UpdateInfo{Available: false}, nil
	}

	u.latestRelease = latestRelease
	latestVer, err := semver.NewVersion(*latestRelease.TagName)
	if err != nil {
		return UpdateInfo{}, fmt.Errorf("error parsing latest Version: %w", err)
	}

	if !latestVer.GreaterThan(currentVer) {
		return UpdateInfo{Available: false}, nil
	}

	// Get releases between current and latest for changelog
	releasesBetween, err := u.getReleasesBetweenTags(u.currentVersion, *latestRelease.TagName)
	if err != nil {
		return UpdateInfo{}, fmt.Errorf("failed to get releases between versions: %w", err)
	}
	u.releasesBetween = releasesBetween

	asset := findAsset(latestRelease.Assets)
	if asset != nil && asset.BrowserDownloadURL != nil {
		size := int64(0)
		if asset.Size != nil {
			size = int64(*asset.Size)
		}
		return UpdateInfo{
			Available:        true,
			Version:          *latestRelease.TagName,
			ReleaseURL:       *latestRelease.HTMLURL,
			DownloadURL:      *asset.BrowserDownloadURL,
			Size:             size,
			AutoUpdate:       autoUpdate,
			RedirectToGitHub: runtime.GOOS != "windows",
		}, nil
	}

	return UpdateInfo{Available: false}, nil
}

func findAsset(assets []*github.ReleaseAsset) *github.ReleaseAsset {
	for _, asset := range assets {
		if asset.Name == nil {
			continue
		}

		name := strings.ToLower(*asset.Name)
		if runtime.GOOS == "windows" {
			if strings.Contains(name, "windows") {
				return asset
			}
		} else {
			// Technically not correct for other unix platforms but since we don't build for them, it is whatever.
			if strings.Contains(name, "macos") {
				return asset
			}
		}
	}

	// Fallback to first asset if available
	if len(assets) > 0 {
		return assets[0]
	}

	return nil
}

func (u *UpdateManager) SetProgressCallback(callback func(float64)) {
	u.progressCallback = callback
}

// GetChangelogs combines changelog from latest release and releases in between
// When latestRelease is not a prerelease, prereleases are filtered out
func (u *UpdateManager) GetChangelogs() []Changelog {
	// UI Testing
	if u.isDev {
		return []Changelog{
			{
				Body:    "## What's Changed\n* **Docs: [Real Phone USB Debugging Guide](https://adbautoplayer.github.io/AdbAutoPlayer/user-guide/real-phone-guide.html)**\n  *Contributed by sieucapoccho*\n* **AFK Journey: Dailies add essence purchase and swap option**\n  *Contributed by @Valextr in https://github.com/AdbAutoPlayer/AdbAutoPlayer/pull/203*\n* **GUI: Improve Error Display for some errors, added Toasts**\n  *Contributed by @yulesxoxo*\n* **GUI: Settings use Accordion Menus and other small improvements**\n  *Contributed by @yulesxoxo*\n* **Global Hotkey (CTRL+SHIFT+ALT+C) to stop the bot**\n  *Contributed by @yulesxoxo in https://github.com/AdbAutoPlayer/AdbAutoPlayer/pull/196*\n* **Make the Summary more depressing**\n  *Contributed by @yulesxoxo in https://github.com/AdbAutoPlayer/AdbAutoPlayer/pull/197*\n* **AFK Journey: Hero exclusion add new Heroes**\n  *Contributed by @yulesxoxo*\n\n\n**Full Changelog**: https://github.com/AdbAutoPlayer/AdbAutoPlayer/compare/8.0.1...8.1.0",
				Version: "1.0.0",
			},
		}
	}

	var changelogs []Changelog

	filterPrereleases := u.latestRelease != nil && !u.latestRelease.GetPrerelease()

	if u.latestRelease != nil && u.latestRelease.Body != nil {
		changelogs = append(changelogs, Changelog{
			Body:    *u.latestRelease.Body,
			Version: *u.latestRelease.TagName,
		})
	}

	for _, release := range u.releasesBetween {
		if release == nil || release.Body == nil {
			continue
		}

		// Skip prereleases if filtering is enabled
		if filterPrereleases && release.GetPrerelease() {
			continue
		}

		changelogs = append(changelogs, Changelog{
			Body:    *release.Body,
			Version: *release.TagName,
		})
	}

	return changelogs
}

func (u *UpdateManager) GetLatestRelease(checkPrerelease bool) (*github.RepositoryRelease, error) {
	var latestRelease *github.RepositoryRelease
	var err error

	if checkPrerelease {
		// Get all releases to include pre-releases/alphas
		latestRelease, err = u.getLatestReleaseIncludingPrerelease()
	} else {
		// Get only the latest stable release
		latestRelease, _, err = u.githubClient.Repositories.GetLatestRelease(getContext(), u.owner, u.repo)
	}

	if err != nil {
		return nil, fmt.Errorf("failed to get latest Release from GitHub: %w", err)
	}

	return latestRelease, nil
}

// getLatestReleaseIncludingPrerelease gets the latest release including pre-releases
func (u *UpdateManager) getLatestReleaseIncludingPrerelease() (*github.RepositoryRelease, error) {
	releases, _, err := u.githubClient.Repositories.ListReleases(getContext(), u.owner, u.repo, &github.ListOptions{
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
func (u *UpdateManager) getReleasesBetweenTags(startTag, endTag string) ([]*github.RepositoryRelease, error) {
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
	releases, _, err := u.githubClient.Repositories.ListReleases(getContext(), u.owner, u.repo, &github.ListOptions{
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

func (u *UpdateManager) downloadFile(url, filepath string) error {
	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer func() {
		if err = resp.Body.Close(); err != nil {
			logger.Get().Errorf("resp.Body.Close error: %v", err)
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
			logger.Get().Errorf("out.Close error: %v", err)
		}
	}()

	// Create a progress reader if callback is set
	var reader io.Reader = resp.Body
	if u.progressCallback != nil && resp.ContentLength > 0 {
		reader = &progressReader{
			reader:   resp.Body,
			total:    resp.ContentLength,
			callback: u.progressCallback,
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

func getContext() context.Context {
	app := application.Get()
	if app == nil {
		return context.Background()
	}
	return app.Context()
}
