package settings

import (
	"os"
	"path/filepath"
	"testing"
)

// TestConfig is a sample struct for testing TOML operations
type TestConfig struct {
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
	filePath := filepath.Join(tempDir, "test_config.toml")

	// Sample config to save
	originalConfig := &TestConfig{
		Name:   "John Doe",
		Age:    30,
		Height: 1.85,
		Active: true,
	}
	originalConfig.Settings.Theme = "dark"
	originalConfig.Settings.Language = "en"

	// Test SaveTOML
	err := SaveTOML(filePath, originalConfig)
	if err != nil {
		t.Fatalf("SaveTOML failed: %v", err)
	}

	// Verify the file was created
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		t.Fatalf("Expected file %s was not created", filePath)
	}

	// Test LoadTOML
	loadedConfig, err := LoadTOML[TestConfig](filePath)
	if err != nil {
		t.Fatalf("LoadTOML failed: %v", err)
	}

	// Verify loaded config matches original
	if loadedConfig.Name != originalConfig.Name {
		t.Errorf("Name mismatch: got %s, want %s", loadedConfig.Name, originalConfig.Name)
	}
	if loadedConfig.Age != originalConfig.Age {
		t.Errorf("Age mismatch: got %d, want %d", loadedConfig.Age, originalConfig.Age)
	}
	if loadedConfig.Height != originalConfig.Height {
		t.Errorf("Height mismatch: got %f, want %f", loadedConfig.Height, originalConfig.Height)
	}
	if loadedConfig.Active != originalConfig.Active {
		t.Errorf("Active mismatch: got %t, want %t", loadedConfig.Active, originalConfig.Active)
	}
	if loadedConfig.Settings.Theme != originalConfig.Settings.Theme {
		t.Errorf("Theme mismatch: got %s, want %s", loadedConfig.Settings.Theme, originalConfig.Settings.Theme)
	}
	if loadedConfig.Settings.Language != originalConfig.Settings.Language {
		t.Errorf("Language mismatch: got %s, want %s", loadedConfig.Settings.Language, originalConfig.Settings.Language)
	}
}

func TestLoadTOML_NonExistentFile(t *testing.T) {
	// Try to load a file that doesn't exist
	tempDir := t.TempDir()
	filePath := filepath.Join(tempDir, "nonexistent.toml")

	_, err := LoadTOML[TestConfig](filePath)
	if err == nil {
		t.Error("Expected error for non-existent file, got nil")
	}
}

func TestSaveTOML_IntToFloatConversion(t *testing.T) {
	// Test that integers are saved without .0 suffix
	tempDir := t.TempDir()
	filePath := filepath.Join(tempDir, "int_test.toml")

	config := &struct {
		Number int
	}{
		Number: 42,
	}

	err := SaveTOML(filePath, config)
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
	filePath := filepath.Join(tempDir, "subdir", "nested", "config.toml")

	config := &TestConfig{
		Name: "Nested Config",
	}

	err := SaveTOML(filePath, config)
	if err != nil {
		t.Fatalf("SaveTOML failed: %v", err)
	}

	// Verify the file was created in nested directory
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		t.Fatalf("Expected file %s was not created", filePath)
	}
}
