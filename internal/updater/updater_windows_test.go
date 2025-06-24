//go:build windows

package updater

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"

	"github.com/google/go-github/v72/github"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestCheckForUpdates_NoUpdateAvailable(t *testing.T) {
	releases := []*github.RepositoryRelease{
		createReleaseWithAsset("1.0.0", "Current version", []string{"app_1.0.0_windows.zip"}, []int{1024000}, false),
	}

	server, client := mockGitHubServer(t, releases)
	defer server.Close()

	ctx := context.Background()
	um := NewUpdateManager(ctx, "1.0.0", false)
	um.githubClient = client

	updateInfo, err := um.CheckForUpdates(false, false)
	require.NoError(t, err)
	assert.False(t, updateInfo.Available)
	assert.Empty(t, updateInfo.Version)
	assert.Empty(t, updateInfo.DownloadURL)
	assert.Equal(t, int64(0), updateInfo.Size)
	assert.False(t, updateInfo.AutoUpdate)
}

func TestCheckForUpdates_UpdateAvailable(t *testing.T) {
	releases := []*github.RepositoryRelease{
		createReleaseWithAsset("1.1.0", "New version available", []string{"app_1.1.0_windows.zip"}, []int{2048000}, false),
	}

	server, client := mockGitHubServer(t, releases)
	defer server.Close()

	ctx := context.Background()
	um := NewUpdateManager(ctx, "1.0.0", false)
	um.githubClient = client

	updateInfo, err := um.CheckForUpdates(true, false)
	require.NoError(t, err)
	assert.True(t, updateInfo.Available)
	assert.Equal(t, "1.1.0", updateInfo.Version)
	assert.Contains(t, updateInfo.DownloadURL, "app_1.1.0_windows.zip")
	assert.Equal(t, int64(2048000), updateInfo.Size)
	assert.True(t, updateInfo.AutoUpdate)
}

func TestCheckForUpdates_PrereleasesIncluded(t *testing.T) {
	releases := []*github.RepositoryRelease{
		createReleaseWithAsset("1.1.0-beta.1", "Beta version", []string{"app_1.1.0-beta.1_windows.zip"}, []int{1536000}, true),
		createReleaseWithAsset("1.0.0", "Stable version", []string{"app_1.0.0_windows.zip"}, []int{1024000}, false),
	}

	server, client := mockGitHubServer(t, releases)
	defer server.Close()

	ctx := context.Background()
	um := NewUpdateManager(ctx, "1.0.0", false)
	um.githubClient = client

	// Test with prereleases enabled
	updateInfo, err := um.CheckForUpdates(false, true)
	require.NoError(t, err)
	assert.True(t, updateInfo.Available)
	assert.Equal(t, "1.1.0-beta.1", updateInfo.Version)
	assert.Contains(t, updateInfo.DownloadURL, "app_1.1.0-beta.1_windows.zip")
	assert.Equal(t, int64(1536000), updateInfo.Size)
	assert.False(t, updateInfo.AutoUpdate)
}

func TestCheckForUpdates_PrereleasesExcluded(t *testing.T) {
	releases := []*github.RepositoryRelease{
		createReleaseWithAsset("1.1.0-beta.1", "Beta version", []string{"app_1.1.0-beta.1_windows.zip"}, []int{1536000}, true),
		createReleaseWithAsset("1.0.0", "Stable version", []string{"app_1.0.0_windows.zip"}, []int{1024000}, false),
	}

	// Create custom server to handle both endpoints
	mux := http.NewServeMux()

	// Mock the latest release endpoint (returns only stable releases)
	mux.HandleFunc("/repos/AdbAutoPlayer/AdbAutoPlayer/releases/latest", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		// Return the stable release (1.0.0)
		stableRelease := releases[1]
		if err := json.NewEncoder(w).Encode(stableRelease); err != nil {
			t.Fatalf("Failed to encode latest release: %v", err)
		}
	})

	server := httptest.NewServer(mux)
	defer server.Close()

	client := github.NewClient(nil)
	requestUrl, _ := url.Parse(server.URL + "/")
	client.BaseURL = requestUrl

	ctx := context.Background()
	um := NewUpdateManager(ctx, "1.0.0", false)
	um.githubClient = client

	// Test with prereleases disabled - should not find any update since current version equals latest stable
	updateInfo, err := um.CheckForUpdates(false, false)
	require.NoError(t, err)
	assert.False(t, updateInfo.Available)
}

func TestCheckForUpdates_CurrentVersionIsPrerelease(t *testing.T) {
	releases := []*github.RepositoryRelease{
		createReleaseWithAsset("1.1.0-beta.2", "Newer beta", []string{"app_1.1.0-beta.2_windows.zip"}, []int{1600000}, true),
		createReleaseWithAsset("1.1.0-beta.1", "Current beta", []string{"app_1.1.0-beta.1_windows.zip"}, []int{1536000}, true),
		createReleaseWithAsset("1.0.0", "Stable version", []string{"app_1.0.0_windows.zip"}, []int{1024000}, false),
	}

	server, client := mockGitHubServer(t, releases)
	defer server.Close()

	ctx := context.Background()
	um := NewUpdateManager(ctx, "1.1.0-beta.1", false)
	um.githubClient = client

	// When current version is prerelease, should automatically check prereleases
	updateInfo, err := um.CheckForUpdates(false, false)
	require.NoError(t, err)
	assert.True(t, updateInfo.Available)
	assert.Equal(t, "1.1.0-beta.2", updateInfo.Version)
}

func TestCheckForUpdates_NoWindowsAsset(t *testing.T) {
	releases := []*github.RepositoryRelease{
		createReleaseWithAsset("1.1.0", "Version without Windows asset", []string{"app_1.1.0_linux.tar.gz"}, []int{1024000}, false),
	}

	server, client := mockGitHubServer(t, releases)
	defer server.Close()

	ctx := context.Background()
	um := NewUpdateManager(ctx, "1.0.0", false)
	um.githubClient = client

	updateInfo, err := um.CheckForUpdates(false, true)
	require.NoError(t, err)
	// Should still be available because findWindowsAsset falls back to first asset
	assert.True(t, updateInfo.Available)
	assert.Equal(t, "1.1.0", updateInfo.Version)
	assert.Contains(t, updateInfo.DownloadURL, "app_1.1.0_linux.tar.gz")
}

func TestCheckForUpdates_NoAssets(t *testing.T) {
	releases := []*github.RepositoryRelease{
		createReleaseWithAsset("1.1.0", "Version without assets", []string{}, []int{}, false),
	}

	server, client := mockGitHubServer(t, releases)
	defer server.Close()

	ctx := context.Background()
	um := NewUpdateManager(ctx, "1.0.0", false)
	um.githubClient = client

	updateInfo, err := um.CheckForUpdates(false, true)
	require.NoError(t, err)
	assert.False(t, updateInfo.Available)
}

func TestCheckForUpdates_InvalidCurrentVersion(t *testing.T) {
	ctx := context.Background()
	um := NewUpdateManager(ctx, "invalid-version", false)

	updateInfo, err := um.CheckForUpdates(false, false)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "failed to parse current version")
	assert.False(t, updateInfo.Available)
}

func TestCheckForUpdates_InvalidLatestVersion(t *testing.T) {
	releases := []*github.RepositoryRelease{
		createReleaseWithAsset("invalid-version", "Invalid semver", []string{"app_invalid_windows.zip"}, []int{1024000}, false),
	}

	server, client := mockGitHubServer(t, releases)
	defer server.Close()

	ctx := context.Background()
	um := NewUpdateManager(ctx, "1.0.0", false)
	um.githubClient = client

	updateInfo, err := um.CheckForUpdates(false, true)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "error parsing latest Version")
	assert.False(t, updateInfo.Available)
}

func TestCheckForUpdates_GitHubAPIError(t *testing.T) {
	// Create a server that returns an error
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer server.Close()

	client := github.NewClient(nil)
	requestUrl, _ := url.Parse(server.URL + "/")
	client.BaseURL = requestUrl

	ctx := context.Background()
	um := NewUpdateManager(ctx, "1.0.0", false)
	um.githubClient = client

	updateInfo, err := um.CheckForUpdates(false, false)
	require.Error(t, err)
	assert.False(t, updateInfo.Available)
}

func TestCheckForUpdates_NilLatestRelease(t *testing.T) {
	// Create a server that returns null for latest release
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, err := w.Write([]byte("null"))
		if err != nil {
			t.Fail()
		}
	}))
	defer server.Close()

	client := github.NewClient(nil)
	requestUrl, _ := url.Parse(server.URL + "/")
	client.BaseURL = requestUrl

	ctx := context.Background()
	um := NewUpdateManager(ctx, "1.0.0", false)
	um.githubClient = client

	updateInfo, err := um.CheckForUpdates(false, false)
	require.NoError(t, err)
	assert.False(t, updateInfo.Available)
}

func TestCheckForUpdates_SetsReleasesBetween(t *testing.T) {
	releases := []*github.RepositoryRelease{
		createReleaseWithAsset("1.2.0", "Latest version", []string{"app_1.2.0_windows.zip"}, []int{2048000}, false),
		createReleaseWithAsset("1.1.0", "Middle version", []string{"app_1.1.0_windows.zip"}, []int{1536000}, false),
		createReleaseWithAsset("1.0.0", "Current version", []string{"app_1.0.0_windows.zip"}, []int{1024000}, false),
	}

	server, client := mockGitHubServer(t, releases)
	defer server.Close()

	ctx := context.Background()
	um := NewUpdateManager(ctx, "1.0.0", false)
	um.githubClient = client

	updateInfo, err := um.CheckForUpdates(false, true)
	require.NoError(t, err)
	assert.True(t, updateInfo.Available)

	// Verify that releasesBetween is populated
	assert.NotNil(t, um.releasesBetween)
	// Should contain version 1.1.0 (between 1.0.0 and 1.2.0)
	found := false
	for _, release := range um.releasesBetween {
		if release.TagName != nil && *release.TagName == "1.1.0" {
			found = true
			break
		}
	}
	assert.True(t, found, "releasesBetween should contain version 1.1.0")
}

// Helper function to create a release with assets that have download URLs and sizes
func createReleaseWithAsset(tagName, body string, assetNames []string, assetSizes []int, prerelease bool) *github.RepositoryRelease {
	release := &github.RepositoryRelease{
		TagName:    &tagName,
		Body:       &body,
		Prerelease: &prerelease,
	}

	for i, assetName := range assetNames {
		downloadURL := "https://github.com/AdbAutoPlayer/AdbAutoPlayer/releases/download/" + tagName + "/" + assetName
		size := 0
		if i < len(assetSizes) {
			size = assetSizes[i]
		}

		asset := &github.ReleaseAsset{
			Name:               &assetName,
			BrowserDownloadURL: &downloadURL,
			Size:               &size,
		}
		release.Assets = append(release.Assets, asset)
	}

	return release
}
