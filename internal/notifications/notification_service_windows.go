package notifications

import (
	"context"
	"github.com/wailsapp/wails/v3/pkg/application"
	"github.com/wailsapp/wails/v3/pkg/services/notifications"
)

func (n *NotificationService) ServiceStartup(ctx context.Context, options application.ServiceOptions) error {
	return notifications.New().ServiceStartup(ctx, options)
}
