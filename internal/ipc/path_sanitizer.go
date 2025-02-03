package ipc

import (
	"os/user"
	"regexp"
	"runtime"
	"strings"
)

type PathSanitizer struct {
	isWindows bool
	username  string
	sanitize  bool
}

func NewPathSanitizer() *PathSanitizer {
	sanitizer := &PathSanitizer{
		isWindows: runtime.GOOS == "windows",
		sanitize:  false,
	}

	currentUser, err := user.Current()
	if err == nil {
		username := currentUser.Username
		if i := strings.LastIndex(username, "\\"); i >= 0 {
			username = username[i+1:]
		}

		sanitizer.username = username
		sanitizer.sanitize = true
	}

	return sanitizer
}

func NewPathSanitizerWithConfig(isWindows bool, username string) *PathSanitizer {
	return &PathSanitizer{
		isWindows: isWindows,
		username:  username,
		sanitize:  true,
	}
}

func (ps *PathSanitizer) SanitizePath(message string) string {
	if !ps.sanitize || strings.Contains(message, "<redacted>") {
		return message
	}

	var pattern, replacement string
	if ps.isWindows {
		pattern = `C:\\Users\\` + regexp.QuoteMeta(ps.username)
		replacement = `C:\Users\<redacted>`
	} else {
		pattern = `/home/` + regexp.QuoteMeta(ps.username)
		replacement = `/home/<redacted>`
	}

	re, err := regexp.Compile(pattern)
	if err != nil {
		return message
	}

	return re.ReplaceAllString(message, replacement)
}
