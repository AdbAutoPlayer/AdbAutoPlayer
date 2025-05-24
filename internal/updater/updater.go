package updater

import (
	"archive/zip"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

func UpdatePatch(assetUrl string) error {
	response, err := http.Get(assetUrl)
	if err != nil {
		return fmt.Errorf("failed to download file: %v", err)
	}
	defer response.Body.Close()

	tempFile, err := os.CreateTemp("", "patch-*.zip")
	if err != nil {
		return fmt.Errorf("failed to create temp file: %v", err)
	}
	defer tempFile.Close()

	_, err = io.Copy(tempFile, response.Body)
	if err != nil {
		return fmt.Errorf("failed to save downloaded file: %v", err)
	}

	zipReader, err := zip.OpenReader(tempFile.Name())
	if err != nil {
		return fmt.Errorf("failed to open zip file: %v", err)
	}
	defer zipReader.Close()

	// Get the absolute path of the target directory
	targetDir, err := filepath.Abs(".")
	if err != nil {
		return fmt.Errorf("failed to get absolute path of target directory: %v", err)
	}

	if err = os.MkdirAll(".", 0755); err != nil {
		return fmt.Errorf("failed to create target directory: %v", err)
	}

	for _, file := range zipReader.File {
		if err = extractFile(file, targetDir); err != nil {
			return err
		}
	}

	return nil
}

func extractFile(file *zip.File, targetDir string) (err error) {
	outputPath := filepath.Join(".", file.Name)

	// Validate the output path to prevent directory traversal (zip slip)
	if strings.Contains(file.Name, "..") || strings.HasPrefix(file.Name, "/") {
		return fmt.Errorf("invalid file path (potential zip slip): %s", file.Name)
	}

	absOutputPath, err := filepath.Abs(outputPath)
	if err != nil {
		return fmt.Errorf("failed to resolve absolute path: %v", err)
	}

	// Check if the resolved path is within the target directory
	if !strings.HasPrefix(absOutputPath, targetDir+string(filepath.Separator)) && absOutputPath != targetDir {
		return fmt.Errorf("invalid file path (potential zip slip): %s", file.Name)
	}

	if file.FileInfo().IsDir() {
		if err = os.MkdirAll(outputPath, 0755); err != nil {
			return fmt.Errorf("failed to create directory: %v", err)
		}
		return nil
	}

	if err = os.MkdirAll(filepath.Dir(outputPath), 0755); err != nil {
		return fmt.Errorf("failed to create directories: %v", err)
	}

	fileInZip, err := file.Open()
	if err != nil {
		return fmt.Errorf("failed to open file in zip archive: %v", err)
	}
	defer func() {
		if cerr := fileInZip.Close(); cerr != nil && err == nil {
			err = fmt.Errorf("failed to close file in zip: %w", cerr)
		}
	}()

	var outputFile *os.File
	const maxRetries = 3
	const timeout = 2 * time.Second

	for attempt := 1; attempt <= maxRetries; attempt++ {
		outputFile, err = os.OpenFile(outputPath, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, file.Mode())
		if err == nil {
			break
		}
		if attempt == maxRetries {
			return fmt.Errorf("failed to create file (attempt %d/%d): %v", attempt, maxRetries, err)
		}
		time.Sleep(timeout)
	}
	defer func() {
		if cerr := outputFile.Close(); cerr != nil && err == nil {
			err = fmt.Errorf("failed to close output file: %w", cerr)
		}
	}()

	for attempt := 1; attempt <= maxRetries; attempt++ {
		_, err = io.Copy(outputFile, fileInZip)
		if err == nil {
			break
		}
		if attempt == maxRetries {
			return fmt.Errorf("failed to copy file data after %d attempts: %v", maxRetries, err)
		}
		time.Sleep(timeout)
	}

	return nil
}
