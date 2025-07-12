package notifications

import (
	"adb-auto-player/internal/logger"
	"adb-auto-player/internal/settings"
	"github.com/google/uuid"
	"github.com/wailsapp/wails/v3/pkg/services/notifications"
	"runtime"
	"sync"
)

var (
	instance *NotificationService
	once     sync.Once
)

type NotificationService struct {
}

// GetService returns the singleton instance of NotificationService
func GetService() *NotificationService {
	once.Do(func() {
		instance = &NotificationService{}
	})
	return instance
}

func (n *NotificationService) SendNotification(title string, body string) string {
	if runtime.GOOS != "windows" || !settings.GetService().GetGeneralSettings().UI.NotificationsEnabled {
		return ""
	}
	id := uuid.New().String()
	err := notifications.New().SendNotification(notifications.NotificationOptions{
		ID:    id,
		Title: title,
		Body:  body,
	})
	if err != nil {
		logger.Get().Errorf("Failed to send Notification: %s", err.Error())
		return ""
	}

	return id
}
