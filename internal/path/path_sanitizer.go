package path

import (
	"os/user"
	"regexp"
	"runtime"
	"strings"
)

type PathSanitizer struct {
	runtime  string
	username string
	sanitize bool
}

func NewPathSanitizer() *PathSanitizer {
	sanitizer := &PathSanitizer{
		runtime:  runtime.GOOS,
		sanitize: false,
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

func NewPathSanitizerWithConfig(runtime string, username string) *PathSanitizer {
	return &PathSanitizer{
		runtime:  runtime,
		username: username,
		sanitize: true,
	}
}

func (ps *PathSanitizer) SanitizePath(message string) string {
	if !ps.sanitize || strings.Contains(message, "{redacted}") {
		return message
	}

	var pattern, replacement string
	if ps.runtime == "windows" {
		pattern = `:\\Users\\` + regexp.QuoteMeta(ps.username)
		replacement = `:\Users\$$env:USERNAME`
	} else if ps.runtime == "darwin" {
		pattern = `/Users/` + regexp.QuoteMeta(ps.username)
		replacement = `/Users/$$USER`
	} else {
		pattern = `/home/` + regexp.QuoteMeta(ps.username)
		replacement = `/home/$$USER`
	}

	re, err := regexp.Compile(pattern)
	if err != nil {
		return message
	}

	return re.ReplaceAllString(message, replacement)
}
