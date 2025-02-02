package main

import (
	"github.com/shirou/gopsutil/process"
)

func IsAdbRunning() bool {
	return getAdbProcess() != nil
}

func KillAdbProcess() {
	adbProcess := getAdbProcess()
	if adbProcess != nil {
		_ = adbProcess.Kill()
	}
}

func getAdbProcess() *process.Process {
	processes, err := process.Processes()
	if err != nil {
		return nil
	}

	for _, p := range processes {
		name, _ := p.Name()
		if name == "adb" || name == "adb.exe" {
			return p
		}
	}
	return nil
}
