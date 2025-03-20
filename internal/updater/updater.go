package updater

import (
	"archive/zip"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
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

	if err = os.MkdirAll(".", 0755); err != nil {
		return fmt.Errorf("failed to create target directory: %v", err)
	}

	for _, file := range zipReader.File {
		outputPath := filepath.Join(".", file.Name)

		if file.FileInfo().IsDir() {
			if err = os.MkdirAll(outputPath, 0755); err != nil {
				return fmt.Errorf("failed to create directory: %v", err)
			}
			continue
		}

		if err = os.MkdirAll(filepath.Dir(outputPath), 0755); err != nil {
			return fmt.Errorf("failed to create directories: %v", err)
		}

		fileInZip, err := file.Open()
		if err != nil {
			return fmt.Errorf("failed to open file in zip archive: %v", err)
		}
		defer fileInZip.Close()

		var outputFile *os.File

		const maxRetries = 3
		const timeout = 2 * time.Second
		for attempt := 1; attempt <= maxRetries; attempt++ {
			outputFile, err = os.OpenFile(outputPath, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, file.Mode())
			if err == nil {
				break
			}
			if attempt == maxRetries {
				return fmt.Errorf("failed to create file (attempt %d/%d): %v\n", attempt, maxRetries, err)
			}
			time.Sleep(timeout)
		}

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
	}

	return nil
}
