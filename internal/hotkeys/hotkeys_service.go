package hotkeys

type HotkeysService struct{}

func (h *HotkeysService) RegisterGlobalHotkeys() error {
	return registerGlobalHotkeys()
}
