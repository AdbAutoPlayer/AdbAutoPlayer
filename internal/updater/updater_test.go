package updater

import "testing"

func TestUpdatePatch(t *testing.T) {
	if err := UpdatePatch("https://github.com/yulesxoxo/AdbAutoPlayer/releases/download/4.4.4/Patch_Windows.zip"); err != nil {
		t.Fatalf("UpdatePatch failed: %v", err)
	}
}
