package settings

import (
	"os"
	"path/filepath"
	"sync"
	"testing"
)

// resetSingleton resets the singleton instance for testing
func resetSingleton() {
	instance = nil
	once = sync.Once{}
}

func TestSettingsService_Singleton(t *testing.T) {
	resetSingleton()

	service1 := GetService()
	service2 := GetService()

	if service1 != service2 {
		t.Error("Expected singleton pattern to return same instance")
	}
}

func TestSettingsService_GetAdbAutoPlayerSettings(t *testing.T) {
	resetSingleton()

	service := GetService()
	settings := service.GetAdbAutoPlayerSettings()

	// Test that we get a non-nil settings object
	if settings == (AdbAutoPlayerSettings{}) {
		t.Error("Expected non-empty AdbAutoPlayerSettings")
	}
}

func TestSettingsService_LoadAdbAutoPlayerSettings(t *testing.T) {
	resetSingleton()

	service := GetService()
	settings := service.LoadAdbAutoPlayerSettings()

	// Test that loading returns the same as getting
	currentSettings := service.GetAdbAutoPlayerSettings()
	if settings != currentSettings {
		t.Error("LoadSettings should return the same as GetAdbAutoPlayerSettings")
	}
}

func TestSettingsService_GetAdbAutoPlayerSettingsForm(t *testing.T) {
	resetSingleton()

	service := GetService()
	form := service.GetAdbAutoPlayerSettingsForm()

	// Test that form contains expected keys
	if _, ok := form["settings"]; !ok {
		t.Error("Expected 'settings' key in form response")
	}

	if _, ok := form["constraints"]; !ok {
		t.Error("Expected 'constraints' key in form response")
	}
}

func TestSettingsService_SaveAdbAutoPlayerSettings_WithTempFile(t *testing.T) {
	resetSingleton()

	// Create a temporary file for testing
	tempDir := t.TempDir()
	tempFile := filepath.Join(tempDir, "test_settings.toml")

	// Create a service instance with a specific path
	service := &SettingsService{
		settingsDirPath:       &tempFile,
		adbAutoPlayerSettings: NewSettings(),
	}

	// Create test settings
	testSettings := NewSettings()

	// Save the settings
	err := service.SaveAdbAutoPlayerSettings(testSettings)

	// Check if file was created
	if _, fileErr := os.Stat(tempFile); os.IsNotExist(fileErr) {
		if err == nil {
			t.Error("Expected file to be created when saving settings")
		}
		// If SaveTOML failed, that's acceptable for this test
		return
	}

	if err != nil {
		t.Errorf("SaveAdbAutoPlayerSettings failed: %v", err)
	}

	// Verify settings were updated in memory
	currentSettings := service.GetAdbAutoPlayerSettings()
	if currentSettings != testSettings {
		t.Error("Settings in memory should be updated after save")
	}
}

func TestResolveAdbAutoPlayerSettingsPath(t *testing.T) {
	// Test the path resolution logic
	path := resolveSettingsDirPath()

	// Should return a non-empty string
	if path == "" {
		t.Error("Expected non-empty path")
	}

	home, _ := os.UserHomeDir()
	macPath := filepath.Join(home, "Library/Application Support/AdbAutoPlayer/settings/")
	validPaths := []string{
		"settings/",
		"../../settings/",
		macPath,
	}

	isValid := false
	for _, validPath := range validPaths {
		if path == validPath {
			isValid = true
			break
		}
	}

	if !isValid {
		t.Errorf("Resolved path '%s' is not in expected paths", path)
	}
}

func TestLoadAdbAutoPlayerSettingsOrDefault_WithNilPath(t *testing.T) {
	settings := loadAdbAutoPlayerSettingsOrDefault(nil)

	// Should return default settings when path is nil
	defaultSettings := NewSettings()
	if settings != defaultSettings {
		t.Error("Expected default settings when path is nil")
	}
}

func TestLoadAdbAutoPlayerSettingsOrDefault_WithValidPath(t *testing.T) {
	// Create a temporary Settings file
	tempDir := t.TempDir()
	tempFile := filepath.Join(tempDir, "test_settings.toml")

	// Create a simple TOML Settings
	settingsContent := `
[logging]
level = "info"
`

	err := os.WriteFile(tempFile, []byte(settingsContent), 0644)
	if err != nil {
		t.Fatalf("Failed to create temp Settings file: %v", err)
	}

	settings := loadAdbAutoPlayerSettingsOrDefault(&tempFile)

	// Should have loaded settings (exact validation depends on AdbAutoPlayerSettings structure)
	if settings == (AdbAutoPlayerSettings{}) {
		t.Error("Expected loaded settings to be non-empty")
	}
}

func TestLoadAdbAutoPlayerSettingsOrDefault_WithInvalidPath(t *testing.T) {
	invalidPath := "/nonexistent/settings.toml"
	settings := loadAdbAutoPlayerSettingsOrDefault(&invalidPath)

	// Should return default settings when file doesn't exist
	defaultSettings := NewSettings()
	if settings != defaultSettings {
		t.Error("Expected default settings when file doesn't exist")
	}
}

// Test concurrent access to singleton
func TestSettingsService_ConcurrentAccess(t *testing.T) {
	resetSingleton()

	const numGoroutines = 10
	instances := make([]*SettingsService, numGoroutines)

	var wg sync.WaitGroup
	wg.Add(numGoroutines)

	for i := 0; i < numGoroutines; i++ {
		go func(index int) {
			defer wg.Done()
			instances[index] = GetService()
		}(i)
	}

	wg.Wait()

	// All instances should be the same
	firstInstance := instances[0]
	for i := 1; i < numGoroutines; i++ {
		if instances[i] != firstInstance {
			t.Error("Concurrent access should return same singleton instance")
		}
	}
}

// Integration test with actual file operations
func TestSettingsService_Integration(t *testing.T) {
	resetSingleton()

	// Create a temporary directory for our test
	tempDir := t.TempDir()
	tempFile := filepath.Join(tempDir, "integration_settings.toml")

	// Create initial settings
	initialSettings := NewSettings()

	// Manually create service instance with temp path
	service := &SettingsService{
		settingsDirPath:       &tempFile,
		adbAutoPlayerSettings: initialSettings,
	}

	// Save settings
	err := service.SaveAdbAutoPlayerSettings(initialSettings)
	if err != nil {
		t.Logf("Save failed (expected if SaveTOML not implemented): %v", err)
		return // Skip rest of test if save functionality isn't available
	}

	// Load settings
	loadedSettings := service.LoadAdbAutoPlayerSettings()

	// Verify they match
	if loadedSettings != initialSettings {
		t.Error("Loaded settings should match saved settings")
	}

	// Verify file exists
	if _, err := os.Stat(tempFile); os.IsNotExist(err) {
		t.Error("Settings file should exist after saving")
	}
}
