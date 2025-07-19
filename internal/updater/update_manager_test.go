package updater

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
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

	// Mock the latest endpoint
	mux.HandleFunc("/repos/AdbAutoPlayer/AdbAutoPlayer/releases/latest", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		// Find the latest non-prerelease version
		var latestRelease *github.RepositoryRelease
		for _, release := range releases {
			if release.Prerelease != nil && !*release.Prerelease {
				if latestRelease == nil {
					latestRelease = release
				} else {
					// Compare versions to find the latest
					// This is a simplified comparison - you might want to use proper semver comparison
					if release.TagName != nil && latestRelease.TagName != nil {
						if *release.TagName > *latestRelease.TagName {
							latestRelease = release
						}
					}
				}
			}
		}

		if latestRelease == nil {
			// Return 404 if no stable release found
			w.WriteHeader(http.StatusNotFound)
			return
		}

		if err := json.NewEncoder(w).Encode(latestRelease); err != nil {
			t.Fatalf("Failed to encode latest release: %v", err)
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
func createRelease(tagName, body string, assets []string, prerelease bool) *github.RepositoryRelease {
	release := &github.RepositoryRelease{
		TagName:    &tagName,
		Body:       &body,
		Prerelease: &prerelease,
	}

	for _, assetName := range assets {
		asset := &github.ReleaseAsset{
			Name: &assetName,
		}
		release.Assets = append(release.Assets, asset)
	}

	return release
}

func TestGetChangelog_DevReturnsDummyData(t *testing.T) {
	um := NewUpdateManager("1.0.0", true)

	// Test with no releases set
	changelog := um.GetChangelogs()
	assert.Equal(t, "1.0.0", changelog[0].Version)
	assert.True(t, strings.HasPrefix(changelog[0].Body, "## What's Changed"))
}

func TestGetChangelog_EmptyReleases(t *testing.T) {
	um := NewUpdateManager("1.0.0", false)

	// Test with no releases set
	changelog := um.GetChangelogs()
	assert.Empty(t, changelog)
}

func TestGetChangelog_LatestReleaseOnly(t *testing.T) {
	um := NewUpdateManager("1.0.0", false)

	releaseTag := "1.1.0"
	releaseBody := `## What's Changed
* **AFK Journey: Fix missing offset in Synergy & CC**
  *Contributed by @yulesxoxo in https://github.com/AdbAutoPlayer/AdbAutoPlayer/pull/184*
* **AFK Journey: Navigation add retry logic when Battle Modes does not open**
  *Contributed by @yulesxoxo in https://github.com/AdbAutoPlayer/AdbAutoPlayer/pull/185*



**Full Changelog**: https://github.com/AdbAutoPlayer/AdbAutoPlayer/compare/8.0.0...8.0.1`

	um.latestRelease = createRelease(releaseTag, releaseBody, []string{"app_1.1.0_windows.zip"}, false)
	um.releasesBetween = []*github.RepositoryRelease{} // Empty

	changelog := um.GetChangelogs()

	assert.Equal(t, releaseBody, changelog[0].Body)
	assert.Equal(t, releaseTag, changelog[0].Version)
}

func TestGetChangelog_WithReleasesBetween(t *testing.T) {
	um := NewUpdateManager("1.0.0", false)

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

	um.latestRelease = createRelease("1.3.0", latestReleaseBody, []string{"app_1.3.0_windows.zip"}, false)
	um.releasesBetween = []*github.RepositoryRelease{
		createRelease("1.2.0", betweenRelease1Body, []string{"app_1.2.0_windows.zip"}, false),
		createRelease("1.1.0", betweenRelease2Body, []string{"app_1.1.0_windows.zip"}, false),
	}

	changelog := um.GetChangelogs()
	assert.Equal(t, latestReleaseBody, changelog[0].Body)
	assert.Equal(t, "1.3.0", changelog[0].Version)
	assert.Equal(t, betweenRelease1Body, changelog[1].Body)
	assert.Equal(t, "1.2.0", changelog[1].Version)
	assert.Equal(t, betweenRelease2Body, changelog[2].Body)
	assert.Equal(t, "1.1.0", changelog[2].Version)
}

func TestGetChangelog_FiltersPrereleasesWhenLatestIsStable(t *testing.T) {
	um := NewUpdateManager("1.0.0", false)

	// Set up test data
	latestReleaseBody := `## Stable Release 1.3.0
* Major feature addition
* Security improvements`

	stableReleaseBody := `## Version 1.2.0
* Added new UI components
* Fixed minor bugs`

	prerelease1Body := `## Version 1.2.1-beta
* Experimental features
* Unstable changes`

	prerelease2Body := `## Version 1.1.1-rc
* Release candidate
* Pre-release fixes`

	um.latestRelease = createRelease("1.3.0", latestReleaseBody, []string{"app_1.3.0_windows.zip"}, false)

	// releasesBetween contains both stable and prerelease versions
	um.releasesBetween = []*github.RepositoryRelease{
		createRelease("1.2.0", stableReleaseBody, []string{"app_1.2.0_windows.zip"}, false),
		createRelease("1.2.1-beta", prerelease1Body, []string{"app_1.2.1-beta_windows.zip"}, true),
		createRelease("1.1.1-rc", prerelease2Body, []string{"app_1.1.1-rc_windows.zip"}, true),
		createRelease("1.1.0", `## Version 1.1.0`, []string{"app_1.1.0_windows.zip"}, false),
	}

	changelog := um.GetChangelogs()

	// Should only include non-prerelease versions
	assert.Equal(t, 3, len(changelog), "Should include only stable releases")
	assert.Equal(t, "1.3.0", changelog[0].Version)
	assert.Equal(t, "1.2.0", changelog[1].Version)
	assert.Equal(t, "1.1.0", changelog[2].Version)

	// Verify prereleases are filtered out
	for _, entry := range changelog {
		assert.False(t, strings.Contains(entry.Version, "-beta"), "Beta prerelease should be filtered out")
		assert.False(t, strings.Contains(entry.Version, "-rc"), "RC prerelease should be filtered out")
	}
}

func TestGetLatestReleaseIncludingPrerelease(t *testing.T) {
	releases := []*github.RepositoryRelease{
		createRelease("2.0.0-beta.1", "Beta release notes", []string{"app_2.0.0-beta.1_windows.zip"}, true),
		createRelease("1.9.0", "Stable release notes", []string{"app_1.9.0_windows.zip"}, false),
		createRelease("1.8.0", "Previous release notes", []string{"app_1.8.0_windows.zip"}, false),
	}

	server, client := mockGitHubServer(t, releases)
	defer server.Close()

	um := NewUpdateManager("1.8.0", false)
	um.githubClient = client

	latest, err := um.getLatestReleaseIncludingPrerelease()
	require.NoError(t, err)
	require.NotNil(t, latest)
	assert.Equal(t, "2.0.0-beta.1", *latest.TagName)
}

func TestGetLatestReleaseIncludingPrerelease_NoUsableAssets(t *testing.T) {
	releases := []*github.RepositoryRelease{
		createRelease("1.1.0", "Release without Windows asset", []string{"app_1.1.0_linux.tar.gz"}, false),
		createRelease("1.0.0", "Release with Windows asset", []string{"app_1.0.0_windows.zip"}, false),
	}

	server, client := mockGitHubServer(t, releases)
	defer server.Close()

	um := NewUpdateManager("0.9.0", false)
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
		createRelease("2.0.0", "Latest release", []string{"app_2.0.0_windows.zip"}, false),
		createRelease("1.9.0", "Release 1.9.0", []string{"app_1.9.0_windows.zip"}, false),
		createRelease("1.8.0", "Release 1.8.0", []string{"app_1.8.0_windows.zip"}, false),
		createRelease("1.7.0", "Release 1.7.0", []string{"app_1.7.0_windows.zip"}, false),
		createRelease("1.6.0", "Release 1.6.0", []string{"app_1.6.0_windows.zip"}, false),
		createRelease("1.5.0", "Release 1.5.0", []string{"app_1.5.0_windows.zip"}, false),
	}

	server, client := mockGitHubServer(t, releases)
	defer server.Close()

	um := NewUpdateManager("1.5.0", false)
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
	um := NewUpdateManager("1.0.0", false)

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
	currentVersion := "1.2.3"
	isDev := true

	um := NewUpdateManager(currentVersion, isDev)

	assert.Equal(t, currentVersion, um.currentVersion)
	assert.Equal(t, isDev, um.isDev)
	assert.Equal(t, "AdbAutoPlayer", um.owner)
	assert.Equal(t, "AdbAutoPlayer", um.repo)
	assert.NotNil(t, um.githubClient)

	expectedProcesses := []string{"adb.exe", "adb_auto_player.exe", "tesseract.exe"}
	assert.Equal(t, expectedProcesses, um.processesToKill)
}

func TestSetProgressCallback(t *testing.T) {
	um := NewUpdateManager("1.0.0", false)

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

func TestGetLatestRelease_StableOnly(t *testing.T) {
	releases := []*github.RepositoryRelease{
		createRelease("2.0.0-beta.1", "Beta release notes", []string{"app_2.0.0-beta.1_windows.zip"}, true),
		createRelease("1.9.0", "Latest stable release", []string{"app_1.9.0_windows.zip"}, false),
		createRelease("1.8.0", "Previous stable release", []string{"app_1.8.0_windows.zip"}, false),
	}

	// Create a custom mux for this test to handle the latest release endpoint
	mux := http.NewServeMux()

	// Mock the latest release endpoint (returns only stable releases)
	mux.HandleFunc("/repos/AdbAutoPlayer/AdbAutoPlayer/releases/latest", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		// GitHub's latest release endpoint returns the latest stable release (1.9.0)
		stableRelease := releases[1] // 1.9.0
		if err := json.NewEncoder(w).Encode(stableRelease); err != nil {
			t.Fatalf("Failed to encode latest release: %v", err)
		}
	})

	server := httptest.NewServer(mux)
	defer server.Close()

	// Create GitHub client pointing to our test server
	client := github.NewClient(nil)
	requestUrl, _ := url.Parse(server.URL + "/")
	client.BaseURL = requestUrl

	um := NewUpdateManager("1.8.0", false)
	um.githubClient = client

	// Test getting stable release only
	latest, err := um.GetLatestRelease(false)
	require.NoError(t, err)
	require.NotNil(t, latest)
	assert.Equal(t, "1.9.0", *latest.TagName)
	assert.Equal(t, "Latest stable release", *latest.Body)
}

func TestGetLatestRelease_IncludingPrerelease(t *testing.T) {
	releases := []*github.RepositoryRelease{
		createRelease("2.0.0-beta.1", "Beta release notes", []string{"app_2.0.0-beta.1_windows.zip"}, true),
		createRelease("1.9.0", "Latest stable release", []string{"app_1.9.0_windows.zip"}, false),
		createRelease("1.8.0", "Previous stable release", []string{"app_1.8.0_windows.zip"}, false),
	}

	server, client := mockGitHubServer(t, releases)
	defer server.Close()

	um := NewUpdateManager("1.8.0", false)
	um.githubClient = client

	// Test getting latest release including prereleases
	latest, err := um.GetLatestRelease(true)
	require.NoError(t, err)
	require.NotNil(t, latest)
	assert.Equal(t, "2.0.0-beta.1", *latest.TagName)
	assert.Equal(t, "Beta release notes", *latest.Body)
}

func TestGetLatestRelease_NetworkError(t *testing.T) {
	// Create a server that immediately closes to simulate network error
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Return 500 to simulate server error
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer server.Close()

	client := github.NewClient(nil)
	requestUrl, _ := url.Parse(server.URL + "/")
	client.BaseURL = requestUrl

	um := NewUpdateManager("1.0.0", false)
	um.githubClient = client

	// Test stable release with network error
	_, err := um.GetLatestRelease(false)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "failed to get latest Release from GitHub")

	// Test prerelease with network error
	_, err = um.GetLatestRelease(true)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "failed to get latest Release from GitHub")
}

func TestGetLatestRelease_EmptyResponse(t *testing.T) {
	// Test case where API returns empty releases list for prereleases
	emptyReleases := []*github.RepositoryRelease{}

	server, client := mockGitHubServer(t, emptyReleases)
	defer server.Close()

	um := NewUpdateManager("1.0.0", false)
	um.githubClient = client

	// Test prerelease with empty response
	_, err := um.GetLatestRelease(true)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "no releases found")
}

func TestGetLatestRelease_NoUsableAssets_Prerelease(t *testing.T) {
	// Test case where latest release has no Windows assets for prereleases
	releases := []*github.RepositoryRelease{
		createRelease("2.0.0-alpha.1", "Alpha without Windows asset", []string{"app_2.0.0-alpha.1_linux.tar.gz"}, false),
		createRelease("1.9.0", "Stable with Windows asset", []string{"app_1.9.0_windows.zip"}, true),
	}

	server, client := mockGitHubServer(t, releases)
	defer server.Close()

	um := NewUpdateManager("1.8.0", false)
	um.githubClient = client

	// Should find the stable release with Windows asset when checking prereleases
	latest, err := um.GetLatestRelease(true)
	require.NoError(t, err)
	require.NotNil(t, latest)
	assert.Equal(t, "1.9.0", *latest.TagName)
}

func TestGetLatestRelease_FallbackToFirstRelease(t *testing.T) {
	// Test the fallback behavior when no release has Windows assets
	releases := []*github.RepositoryRelease{
		createRelease("2.0.0", "Latest without Windows asset", []string{"app_2.0.0_linux.tar.gz"}, true),
		createRelease("1.9.0", "Previous without Windows asset", []string{"app_1.9.0_mac.dmg"}, true),
	}

	server, client := mockGitHubServer(t, releases)
	defer server.Close()

	um := NewUpdateManager("1.8.0", false)
	um.githubClient = client

	// Should fallback to first release when no Windows assets found
	latest, err := um.GetLatestRelease(true)
	require.NoError(t, err)
	require.NotNil(t, latest)
	assert.Equal(t, "2.0.0", *latest.TagName)
}

func TestGetLatestRelease_BothStableAndPrerelease(t *testing.T) {
	// Test to ensure both code paths work with the same setup
	releases := []*github.RepositoryRelease{
		createRelease("2.0.0-rc.1", "Release candidate", []string{"app_2.0.0-rc.1_windows.zip"}, false),
		createRelease("1.9.0", "Latest stable", []string{"app_1.9.0_windows.zip"}, true),
	}

	// Setup server for both endpoints
	mux := http.NewServeMux()

	// Mock the releases list endpoint
	mux.HandleFunc("/repos/AdbAutoPlayer/AdbAutoPlayer/releases", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(releases); err != nil {
			t.Fatalf("Failed to encode releases: %v", err)
		}
	})

	// Mock the latest release endpoint
	mux.HandleFunc("/repos/AdbAutoPlayer/AdbAutoPlayer/releases/latest", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		// Return the latest stable release
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

	um := NewUpdateManager("1.8.0", false)
	um.githubClient = client

	// Test stable release
	stableRelease, err := um.GetLatestRelease(false)
	require.NoError(t, err)
	require.NotNil(t, stableRelease)
	assert.Equal(t, "1.9.0", *stableRelease.TagName)

	// Test prerelease
	prereleaseRelease, err := um.GetLatestRelease(true)
	require.NoError(t, err)
	require.NotNil(t, prereleaseRelease)
	assert.Equal(t, "2.0.0-rc.1", *prereleaseRelease.TagName)
}
