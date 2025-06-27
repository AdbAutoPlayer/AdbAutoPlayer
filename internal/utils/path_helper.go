package utils

import "os"

func GetFirstPathThatExists(paths []string) *string {
	for _, path := range paths {
		if stat, _ := os.Stat(path); stat != nil {
			return &path
		}
	}

	return nil
}
