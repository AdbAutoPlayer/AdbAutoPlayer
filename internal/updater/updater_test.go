package updater

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"

	"github.com/google/go-github/v72/github"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// mockGitHubServer creates a test server that mocks GitHub API responses
func mockGitHubServer(t *testing.T, releases []*github.RepositoryRelease) (*httptest.Server, *github.Client) {
	mux := http.NewServeMux()

	// Mock the releases endpoint
	mux.HandleFunc("/repos/AdbAutoPlayer/AdbAutoPlayer/releases", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		// Parse query parameters to handle pagination
		perPage := 30 // default
		if pp := r.URL.Query().Get("per_page"); pp != "" {
			_, _ = fmt.Sscanf(pp, "%d", &perPage)
		}

		// Return up to perPage releases
		responseReleases := releases
		if len(releases) > perPage {
			responseReleases = releases[:perPage]
		}

		if err := json.NewEncoder(w).Encode(responseReleases); err != nil {
			t.Fatalf("Failed to encode releases: %v", err)
		}
	})

	server := httptest.NewServer(mux)

	// Create GitHub client pointing to our test server
	client := github.NewClient(nil)
	requestUrl, _ := url.Parse(server.URL + "/")
	client.BaseURL = requestUrl

	return server, client
}

// Helper function to create a release pointer
func createRelease(tagName, body string, assets []string) *github.RepositoryRelease {
	release := &github.RepositoryRelease{
		TagName: &tagName,
		Body:    &body,
	}

	for _, assetName := range assets {
		asset := &github.ReleaseAsset{
			Name: &assetName,
		}
		release.Assets = append(release.Assets, asset)
	}

	return release
}

func TestGetChangelog_EmptyReleases(t *testing.T) {
	ctx := context.Background()
	um := NewUpdateManager(ctx, "1.0.0", false)

	// Test with no releases set
	changelog := um.GetChangelogs()
	assert.Empty(t, changelog)
}

func TestGetChangelog_LatestReleaseOnly(t *testing.T) {
	ctx := context.Background()
	um := NewUpdateManager(ctx, "1.0.0", false)

	releaseTag := "1.1.0"
	releaseBody := `## What's Changed
* **AFK Journey: Fix missing offset in Synergy & CC**
  *Contributed by @yulesxoxo in https://github.com/AdbAutoPlayer/AdbAutoPlayer/pull/184*
* **AFK Journey: Navigation add retry logic when Battle Modes does not open**
  *Contributed by @yulesxoxo in https://github.com/AdbAutoPlayer/AdbAutoPlayer/pull/185*



**Full Changelog**: https://github.com/AdbAutoPlayer/AdbAutoPlayer/compare/8.0.0...8.0.1`

	um.latestRelease = createRelease(releaseTag, releaseBody, []string{"app_1.1.0_windows.zip"})
	um.releasesBetween = []*github.RepositoryRelease{} // Empty

	changelog := um.GetChangelogs()

	assert.Equal(t, releaseBody, changelog[0].Body)
	assert.Equal(t, releaseTag, changelog[0].Version)
}

func TestGetChangelog_WithReleasesBetween(t *testing.T) {
	ctx := context.Background()
	um := NewUpdateManager(ctx, "1.0.0", false)

	// Set up test data - placeholder JSON responses you can fill in
	latestReleaseBody := `## Latest Release Changes
* Major feature addition
* Security improvements

**Full Changelog**: https://github.com/AdbAutoPlayer/AdbAutoPlayer/compare/1.2.0...1.3.0`

	betweenRelease1Body := `## Version 1.2.0
* Added new UI components
* Fixed minor bugs

**Full Changelog**: https://github.com/AdbAutoPlayer/AdbAutoPlayer/compare/1.1.0...1.2.0`

	betweenRelease2Body := `## Version 1.1.0
* Initial feature set
* Basic functionality

**Full Changelog**: https://github.com/AdbAutoPlayer/AdbAutoPlayer/compare/1.0.0...1.1.0`

	um.latestRelease = createRelease("1.3.0", latestReleaseBody, []string{"app_1.3.0_windows.zip"})
	um.releasesBetween = []*github.RepositoryRelease{
		createRelease("1.2.0", betweenRelease1Body, []string{"app_1.2.0_windows.zip"}),
		createRelease("1.1.0", betweenRelease2Body, []string{"app_1.1.0_windows.zip"}),
	}

	changelog := um.GetChangelogs()
	assert.Equal(t, latestReleaseBody, changelog[0].Body)
	assert.Equal(t, "1.3.0", changelog[0].Version)
	assert.Equal(t, betweenRelease1Body, changelog[1].Body)
	assert.Equal(t, "1.2.0", changelog[1].Version)
	assert.Equal(t, betweenRelease2Body, changelog[2].Body)
	assert.Equal(t, "1.1.0", changelog[2].Version)
}

func TestGetLatestReleaseIncludingPrerelease(t *testing.T) {
	releases := []*github.RepositoryRelease{
		createRelease("2.0.0-beta.1", "Beta release notes", []string{"app_2.0.0-beta.1_windows.zip"}),
		createRelease("1.9.0", "Stable release notes", []string{"app_1.9.0_windows.zip"}),
		createRelease("1.8.0", "Previous release notes", []string{"app_1.8.0_windows.zip"}),
	}

	server, client := mockGitHubServer(t, releases)
	defer server.Close()

	ctx := context.Background()
	um := NewUpdateManager(ctx, "1.8.0", false)
	um.githubClient = client

	latest, err := um.getLatestReleaseIncludingPrerelease()
	require.NoError(t, err)
	require.NotNil(t, latest)
	assert.Equal(t, "2.0.0-beta.1", *latest.TagName)
}

func TestGetLatestReleaseIncludingPrerelease_NoUsableAssets(t *testing.T) {
	releases := []*github.RepositoryRelease{
		createRelease("1.1.0", "Release without Windows asset", []string{"app_1.1.0_linux.tar.gz"}),
		createRelease("1.0.0", "Release with Windows asset", []string{"app_1.0.0_windows.zip"}),
	}

	server, client := mockGitHubServer(t, releases)
	defer server.Close()

	ctx := context.Background()
	um := NewUpdateManager(ctx, "0.9.0", false)
	um.githubClient = client

	latest, err := um.getLatestReleaseIncludingPrerelease()
	require.NoError(t, err)
	require.NotNil(t, latest)
	// Should return the release with Windows asset
	assert.Equal(t, "1.0.0", *latest.TagName)
}

func TestGetReleasesBetweenTags(t *testing.T) {
	releases := []*github.RepositoryRelease{
		// Placeholder - replace with actual release data in descending order
		createRelease("2.0.0", "Latest release", []string{"app_2.0.0_windows.zip"}),
		createRelease("1.9.0", "Release 1.9.0", []string{"app_1.9.0_windows.zip"}),
		createRelease("1.8.0", "Release 1.8.0", []string{"app_1.8.0_windows.zip"}),
		createRelease("1.7.0", "Release 1.7.0", []string{"app_1.7.0_windows.zip"}),
		createRelease("1.6.0", "Release 1.6.0", []string{"app_1.6.0_windows.zip"}),
		createRelease("1.5.0", "Release 1.5.0", []string{"app_1.5.0_windows.zip"}),
	}

	server, client := mockGitHubServer(t, releases)
	defer server.Close()

	ctx := context.Background()
	um := NewUpdateManager(ctx, "1.5.0", false)
	um.githubClient = client

	between, err := um.getReleasesBetweenTags("1.6.0", "1.9.0")
	require.NoError(t, err)

	// Should return releases 1.7.0 and 1.8.0 (between 1.6.0 and 1.9.0, exclusive)
	assert.Len(t, between, 2)

	// Verify the releases are the expected ones
	tags := make([]string, len(between))
	for i, release := range between {
		tags[i] = *release.TagName
	}
	assert.Contains(t, tags, "1.7.0")
	assert.Contains(t, tags, "1.8.0")
}

func TestGetReleasesBetweenTags_InvalidVersions(t *testing.T) {
	ctx := context.Background()
	um := NewUpdateManager(ctx, "1.0.0", false)

	// Test with invalid start tag
	_, err := um.getReleasesBetweenTags("invalid-version", "1.1.0")
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "invalid start tag")

	// Test with invalid end tag
	_, err = um.getReleasesBetweenTags("1.0.0", "invalid-version")
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "invalid end tag")
}

func TestNewUpdateManager(t *testing.T) {
	ctx := context.Background()
	currentVersion := "1.2.3"
	isDev := true

	um := NewUpdateManager(ctx, currentVersion, isDev)

	assert.Equal(t, ctx, um.ctx)
	assert.Equal(t, currentVersion, um.currentVersion)
	assert.Equal(t, isDev, um.isDev)
	assert.Equal(t, "AdbAutoPlayer", um.owner)
	assert.Equal(t, "AdbAutoPlayer", um.repo)
	assert.NotNil(t, um.githubClient)

	expectedProcesses := []string{"adb.exe", "adb_auto_player.exe", "tesseract.exe"}
	assert.Equal(t, expectedProcesses, um.processesToKill)
}

func TestSetProgressCallback(t *testing.T) {
	ctx := context.Background()
	um := NewUpdateManager(ctx, "1.0.0", false)

	callbackCalled := false
	callback := func(progress float64) {
		callbackCalled = true
	}

	um.SetProgressCallback(callback)
	assert.NotNil(t, um.progressCallback)

	// Test that callback is actually set
	if um.progressCallback != nil {
		um.progressCallback(50.0)
		assert.True(t, callbackCalled)
	}
}
