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
	service := notifications.New()
	if nil == service {
		return ""
	}

	_ = service.RemoveAllDeliveredNotifications()
	_ = service.RemoveAllPendingNotifications()
	id := uuid.New().String()
	err := service.SendNotification(notifications.NotificationOptions{
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
