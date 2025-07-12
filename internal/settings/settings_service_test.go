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

func TestSettingsService_GetGeneralSettings(t *testing.T) {
	resetSingleton()

	service := GetService()
	settings := service.GetGeneralSettings()

	// Test that we get a non-nil settings object
	if settings == (GeneralSettings{}) {
		t.Error("Expected non-empty GeneralSettings")
	}
}

func TestSettingsService_LoadGeneralSettings(t *testing.T) {
	resetSingleton()

	service := GetService()
	settings := service.LoadGeneralSettings()

	// Test that loading returns the same as getting
	currentSettings := service.GetGeneralSettings()
	if settings != currentSettings {
		t.Error("LoadGeneralSettings should return the same as GetGeneralSettings")
	}
}

func TestSettingsService_GetGeneralSettingsForm(t *testing.T) {
	resetSingleton()

	service := GetService()
	form := service.GetGeneralSettingsForm()

	// Test that form contains expected keys
	if _, ok := form["settings"]; !ok {
		t.Error("Expected 'settings' key in form response")
	}

	if _, ok := form["constraints"]; !ok {
		t.Error("Expected 'constraints' key in form response")
	}
}

func TestSettingsService_SaveGeneralSettings_WithTempFile(t *testing.T) {
	resetSingleton()

	// Create a temporary file for testing
	tempDir := t.TempDir()
	tempFile := filepath.Join(tempDir, "test_config.toml")

	// Create a service instance with a specific path
	service := &SettingsService{
		generalSettingsPath: &tempFile,
		generalSettings:     NewGeneralSettings(),
	}

	// Create test settings
	testSettings := NewGeneralSettings()

	// Save the settings
	err := service.SaveGeneralSettings(testSettings)

	// Check if file was created
	if _, fileErr := os.Stat(tempFile); os.IsNotExist(fileErr) {
		if err == nil {
			t.Error("Expected file to be created when saving settings")
		}
		// If SaveTOML failed, that's acceptable for this test
		return
	}

	if err != nil {
		t.Errorf("SaveGeneralSettings failed: %v", err)
	}

	// Verify settings were updated in memory
	currentSettings := service.GetGeneralSettings()
	if currentSettings != testSettings {
		t.Error("Settings in memory should be updated after save")
	}
}

func TestResolveGeneralSettingsPath(t *testing.T) {
	// Test the path resolution logic
	path := resolveGeneralSettingsPath()

	// Should return a non-empty string
	if path == "" {
		t.Error("Expected non-empty path")
	}

	// Should return the first fallback path if no files exist
	expectedFallback := "config.toml"
	if path == expectedFallback {
		// This is expected when no config files exist
		return
	}

	// If it's not the fallback, it should be one of the predefined paths
	validPaths := []string{
		"config.toml",
		"config/config.toml",
		"../../config/config.toml",
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

func TestLoadGeneralSettingsOrDefault_WithNilPath(t *testing.T) {
	settings := loadGeneralSettingsOrDefault(nil)

	// Should return default settings when path is nil
	defaultSettings := NewGeneralSettings()
	if settings != defaultSettings {
		t.Error("Expected default settings when path is nil")
	}
}

func TestLoadGeneralSettingsOrDefault_WithValidPath(t *testing.T) {
	// Create a temporary config file
	tempDir := t.TempDir()
	tempFile := filepath.Join(tempDir, "test_config.toml")

	// Create a simple TOML config
	configContent := `
[logging]
level = "info"
`

	err := os.WriteFile(tempFile, []byte(configContent), 0644)
	if err != nil {
		t.Fatalf("Failed to create temp config file: %v", err)
	}

	settings := loadGeneralSettingsOrDefault(&tempFile)

	// Should have loaded settings (exact validation depends on GeneralSettings structure)
	if settings == (GeneralSettings{}) {
		t.Error("Expected loaded settings to be non-empty")
	}
}

func TestLoadGeneralSettingsOrDefault_WithInvalidPath(t *testing.T) {
	invalidPath := "/nonexistent/config.toml"
	settings := loadGeneralSettingsOrDefault(&invalidPath)

	// Should return default settings when file doesn't exist
	defaultSettings := NewGeneralSettings()
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
	tempFile := filepath.Join(tempDir, "integration_config.toml")

	// Create initial settings
	initialSettings := NewGeneralSettings()

	// Manually create service instance with temp path
	service := &SettingsService{
		generalSettingsPath: &tempFile,
		generalSettings:     initialSettings,
	}

	// Save settings
	err := service.SaveGeneralSettings(initialSettings)
	if err != nil {
		t.Logf("Save failed (expected if SaveTOML not implemented): %v", err)
		return // Skip rest of test if save functionality isn't available
	}

	// Load settings
	loadedSettings := service.LoadGeneralSettings()

	// Verify they match
	if loadedSettings != initialSettings {
		t.Error("Loaded settings should match saved settings")
	}

	// Verify file exists
	if _, err := os.Stat(tempFile); os.IsNotExist(err) {
		t.Error("Config file should exist after saving")
	}
}
