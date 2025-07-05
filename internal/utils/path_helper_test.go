package utils

import (
	"os"
	"path/filepath"
	"testing"
)

func TestGetFirstPathThatExists(t *testing.T) {
	// Setup: Create some temporary files and directories for testing
	tempDir := t.TempDir()
	existingFile1 := filepath.Join(tempDir, "file1.txt")
	existingFile2 := filepath.Join(tempDir, "file2.txt")
	nonExistingFile := filepath.Join(tempDir, "nonexistent.txt")

	// Create test files
	if err := os.WriteFile(existingFile1, []byte("test"), 0644); err != nil {
		t.Fatalf("Failed to create test file: %v", err)
	}
	if err := os.WriteFile(existingFile2, []byte("test"), 0644); err != nil {
		t.Fatalf("Failed to create test file: %v", err)
	}

	tests := []struct {
		name     string
		paths    []string
		expected *string
	}{
		{
			name:     "single existing path",
			paths:    []string{existingFile1},
			expected: &existingFile1,
		},
		{
			name:     "multiple paths with first existing",
			paths:    []string{existingFile1, existingFile2, nonExistingFile},
			expected: &existingFile1,
		},
		{
			name:     "multiple paths with middle existing",
			paths:    []string{nonExistingFile, existingFile1, existingFile2},
			expected: &existingFile1,
		},
		{
			name:     "multiple paths with last existing",
			paths:    []string{nonExistingFile, "another_fake_path.txt", existingFile2},
			expected: &existingFile2,
		},
		{
			name:     "no existing paths",
			paths:    []string{nonExistingFile, "fake_path.txt"},
			expected: nil,
		},
		{
			name:     "empty input",
			paths:    []string{},
			expected: nil,
		},
		{
			name:     "directory exists",
			paths:    []string{tempDir, existingFile1},
			expected: &tempDir,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := GetFirstPathThatExists(tt.paths)

			if tt.expected == nil && result != nil {
				t.Errorf("Expected nil, got %v", *result)
			} else if tt.expected != nil && result == nil {
				t.Errorf("Expected %v, got nil", *tt.expected)
			} else if tt.expected != nil && result != nil && *tt.expected != *result {
				t.Errorf("Expected %v, got %v", *tt.expected, *result)
			}
		})
	}
}
