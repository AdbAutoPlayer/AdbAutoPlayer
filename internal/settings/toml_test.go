package settings

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestSettings is a sample struct for testing TOML operations
type TestSettings struct {
	Name     string
	Age      int
	Height   float64
	Active   bool
	Settings struct {
		Theme    string
		Language string
	}
}

func TestLoadAndSaveTOML(t *testing.T) {
	// Create a temporary directory for test files
	tempDir := t.TempDir()
	filePath := filepath.Join(tempDir, "test_settings.toml")

	// Sample Settings to save
	originalSettings := &TestSettings{
		Name:   "John Doe",
		Age:    30,
		Height: 1.85,
		Active: true,
	}
	originalSettings.Settings.Theme = "dark"
	originalSettings.Settings.Language = "en"

	// Test SaveTOML
	err := SaveTOML(filePath, originalSettings)
	if err != nil {
		t.Fatalf("SaveTOML failed: %v", err)
	}

	// Verify the file was created
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		t.Fatalf("Expected file %s was not created", filePath)
	}

	// Test LoadTOML
	loadedSettings, err := LoadTOML[TestSettings](filePath)
	if err != nil {
		t.Fatalf("LoadTOML failed: %v", err)
	}

	// Verify loaded Settings matches original
	if loadedSettings.Name != originalSettings.Name {
		t.Errorf("Name mismatch: got %s, want %s", loadedSettings.Name, originalSettings.Name)
	}
	if loadedSettings.Age != originalSettings.Age {
		t.Errorf("Age mismatch: got %d, want %d", loadedSettings.Age, originalSettings.Age)
	}
	if loadedSettings.Height != originalSettings.Height {
		t.Errorf("Height mismatch: got %f, want %f", loadedSettings.Height, originalSettings.Height)
	}
	if loadedSettings.Active != originalSettings.Active {
		t.Errorf("Active mismatch: got %t, want %t", loadedSettings.Active, originalSettings.Active)
	}
	if loadedSettings.Settings.Theme != originalSettings.Settings.Theme {
		t.Errorf("Theme mismatch: got %s, want %s", loadedSettings.Settings.Theme, originalSettings.Settings.Theme)
	}
	if loadedSettings.Settings.Language != originalSettings.Settings.Language {
		t.Errorf("Language mismatch: got %s, want %s", loadedSettings.Settings.Language, originalSettings.Settings.Language)
	}
}

func TestLoadTOML_NonExistentFile(t *testing.T) {
	// Try to load a file that doesn't exist
	tempDir := t.TempDir()
	filePath := filepath.Join(tempDir, "nonexistent.toml")

	_, err := LoadTOML[TestSettings](filePath)
	if err == nil {
		t.Error("Expected error for non-existent file, got nil")
	}
}

func TestSaveTOML_IntToFloatConversion(t *testing.T) {
	// Test that integers are saved without .0 suffix
	tempDir := t.TempDir()
	filePath := filepath.Join(tempDir, "int_test.toml")

	settings := &struct {
		Number int
	}{
		Number: 42,
	}

	err := SaveTOML(filePath, settings)
	if err != nil {
		t.Fatalf("SaveTOML failed: %v", err)
	}

	// Read the raw file content to verify the format
	content, err := os.ReadFile(filePath)
	if err != nil {
		t.Fatalf("Failed to read file: %v", err)
	}

	contentStr := string(content)
	expected := "Number = 42\n"
	if contentStr != expected {
		t.Errorf("Unexpected TOML content:\ngot:\n%s\nwant:\n%s", contentStr, expected)
	}
}

func TestSaveTOML_CreatesDirectories(t *testing.T) {
	// Test that SaveTOML creates parent directories
	tempDir := t.TempDir()
	filePath := filepath.Join(tempDir, "subdir", "nested", "settings.toml")

	settings := &TestSettings{
		Name: "Nested Setting",
	}

	err := SaveTOML(filePath, settings)
	if err != nil {
		t.Fatalf("SaveTOML failed: %v", err)
	}

	// Verify the file was created in nested directory
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		t.Fatalf("Expected file %s was not created", filePath)
	}
}

func TestLoadTOML(t *testing.T) {
	adbAutoPlayerSettings, err := LoadTOML[AdbAutoPlayerSettings]("../../settings/AdbAutoPlayer.toml")
	if err != nil {
		t.Errorf("[Error LoadTOML()] %v", err)
		return
	}
	assert.Equal(t, "127.0.0.1:7555", adbAutoPlayerSettings.Device.ID)
}

func TestSaveTOML(t *testing.T) {
	testFilePath := "test_settings.toml"

	deleteFileIfExists(testFilePath, t)

	mainSettings := NewSettings()

	if err := SaveTOML[AdbAutoPlayerSettings](testFilePath, &mainSettings); err != nil {
		t.Errorf("[Error SaveTOML()] %v", err)
		return
	}

	if _, err := os.Stat(testFilePath); os.IsNotExist(err) {
		t.Errorf("[Error] File does not exist after SaveTOML")
		return
	}

	deleteFileIfExists(testFilePath, t)
}

func deleteFileIfExists(filePath string, t *testing.T) {
	if _, err := os.Stat(filePath); err == nil {
		err = os.Remove(filePath)
		if err != nil {
			t.Errorf("[Error removing existing test file] %v", err)
		}
	}
}
