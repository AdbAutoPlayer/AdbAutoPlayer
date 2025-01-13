package adb

import (
	"adb-auto-player/internal/config"
	"fmt"
	"github.com/electricbubble/gadb"
	"strings"
)

var inMemoryClient *gadb.Client
var inMemoryDevice *gadb.Device

func GetClient() (*gadb.Client, error) {
	if inMemoryClient != nil {
		return inMemoryClient, nil
	}
	loadConfig, err := config.LoadConfig[config.MainConfig]("config.toml")
	if err != nil {
		return nil, err
	}
	adbClient, err := gadb.NewClientWith(
		loadConfig.ADB.Host,
		loadConfig.ADB.Port,
	)
	if err != nil {
		return nil, err
	}
	inMemoryClient = &adbClient
	return inMemoryClient, nil
}

func GetDevice() (*gadb.Device, error) {
	if inMemoryDevice != nil {
		return inMemoryDevice, nil
	}

	adbClient, err := GetClient()
	if err != nil {
		return nil, err
	}

	mainConfig, err := config.LoadConfig[config.MainConfig]("config.toml")
	if err != nil {
		return nil, err
	}
	serial := mainConfig.Device.ID
	deviceList, err := adbClient.DeviceList()
	if err != nil {
		return nil, err
	}

	if len(deviceList) == 0 {
		return nil, fmt.Errorf("ADB: no devices found")
	}

	for _, tmpDevice := range deviceList {
		if tmpDevice.Serial() == serial {
			inMemoryDevice = &tmpDevice
			return inMemoryDevice, nil
		}
	}

	inMemoryDevice = &deviceList[0]
	return inMemoryDevice, nil
}

func GetRunningAppPackageName() (*string, error) {
	device, err := GetDevice()
	if err != nil {
		return nil, err
	}
	cmd := "dumpsys activity activities | grep ResumedActivity | cut -d \"{\" -f2 | cut -d ' ' -f3 | cut -d \"/\" -f1"
	value, err := device.RunShellCommand(cmd)
	if err != nil {
		return nil, err
	}

	if idx := strings.Index(value, "\n"); idx != -1 {
		value = value[:idx]
	}
	return &value, nil
}
