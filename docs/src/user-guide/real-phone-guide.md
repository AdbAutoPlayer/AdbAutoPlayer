# Real Phone USB Debugging Setup Guide

A comprehensive guide to enable USB debugging on popular Android phone brands for AdbAutoPlayer.

---

## Table of Contents

- [AdbAutoPlayer Configuration](#adbautoplayer-configuration)
- [Important Considerations](#important-considerations)
- [Prerequisites](#prerequisites)
- [Universal Steps](#universal-steps)
- [Brand-Specific Instructions](#brand-specific-instructions)
    - [Samsung](#samsung)
    - [Google Pixel](#google-pixel)
    - [OnePlus](#oneplus)
    - [Xiaomi/MIUI](#xiaomimiui)
    - [Huawei/Honor](#huaweiHonor)
    - [Oppo](#oppo)
    - [Vivo](#vivo)
    - [Sony](#sony)
    - [LG](#lg)
    - [Motorola](#motorola)
- [Troubleshooting](#troubleshooting)

---

## AdbAutoPlayer Configuration

![device-config.png](../images/real-phone/device-config.png)

### Device Settings in AdbAutoPlayer

| Setting              | Description                                                              |
|----------------------|--------------------------------------------------------------------------|
| **"Resize Display"** | Enable this - Changes your display size to 1080x1920 when the bot starts |
| **Resolution**       | Set to **1080x1920** for optimal compatibility                           |

---

## Important Considerations

> [!WARNING]
> **Security Notes:**
> - **USB debugging** grants full control over your device
> - Always use **trusted computers** and **quality USB cables**
> - Consider **disabling USB debugging** when not actively using automation
> - Some **banking and security apps** may detect developer mode
> - Always **revoke USB debugging authorizations** from untrusted computers
> - Consider security implications before enabling **OEM unlocking**

> [!CAUTION]
> **Device Health Notes:**
> - **Avoid using the bot** when your device temperature is too high
> - High temperatures can cause **permanent damage** to battery and components

---

## Prerequisites

Before starting, ensure you have:

| Requirement         | Details                                                                                        |
|---------------------|------------------------------------------------------------------------------------------------|
| **USB Cable**       | Must support **data transfer** (most modern cables do, but some old ones are charge-only)      |
| **Admin Rights**    | Administrative privileges on your computer                                                     |
| **Android Version** | Android 4.2 (API level 17) or higher                                                           |

---

## Universal Steps

These steps apply to **ALL** Android devices, regardless of brand:

### Step 1: Enable Developer Options

1. **Open Settings** on your Android device
2. **Scroll down** and tap **"About phone"** or **"About device"**
3. **Find "Build number"** (location varies by brand - see brand-specific sections below)
4. **Tap "Build number" 7 times rapidly**
    - You'll see countdown: *"You are now X steps away from being a developer"*
    - After 7 taps: *"You are now a developer!"* or *"Developer mode has been enabled"*
5. **Go back** to the main Settings menu
6. **Look for "Developer options"** (usually under System, Additional settings, or directly in Settings)

### Step 2: Enable USB Debugging

1. **Open "Developer options"**
2. **Toggle "Developer options" ON** (if there's a master switch at the top and it's off)
3. **Scroll down** and find **"USB debugging"**
4. **Toggle "USB debugging" ON**
5. **Confirm** when prompted with *"Allow USB debugging?"*
6. **Check if there are more options that start with USB debugging like "USB debugging (Security settings)" if yes Toggle ON**

### Step 3: Additional Developer Settings (Optional but Recommended)

While in Developer options, consider enabling these for better automation:

| Setting                                 | Purpose                                               |
|-----------------------------------------|-------------------------------------------------------|
| **"Stay awake"**                        | Keeps screen on while charging                        |
| **"Disable adb authorization timeout"** | Prevents repeated authorization prompts (Android 11+) |

---

## Brand-Specific Instructions

### Samsung

**Build Number Location:**
- **Samsung One UI 4.x** and **Samsung One UI 5.0+**:
  ```
  Settings → About phone → Software information → Build number
  ```
- **Older Samsung**:
  ```
  Settings → About device → Build number
  ```

**Additional Samsung Steps:**
- After enabling Developer options, you may need to **restart** your phone
- In Developer options, look for **"USB debugging"** under the **Debugging** section
- Samsung devices may show additional security warnings - tap **"OK"** to proceed
- Some Samsung devices have **"Developer options"** under **Settings → Developer options** directly

**Knox Security Note:**
- Samsung Knox may interfere with automation
- If you encounter issues, try disabling Knox security features (this may void warranty)

---

### Google Pixel

**Build Number Location:**
- **Android 12+**:
  ```
  Settings → About phone → Build number
  ```
- **Android 8-11**:
  ```
  Settings → System → About phone → Build number
  ```
- **Android 7 and below**:
  ```
  Settings → About phone → Build number
  ```

**Additional Pixel Steps:**
- **"Developer options"** appears under **Settings → System → Developer options**
- Pixel devices typically have the cleanest Android experience with minimal restrictions

---

### OnePlus

**Build Number Location:**
- **OxygenOS 12+**:
  ```
  Settings → About device → Version → Build number
  ```
- **OxygenOS 11**:
  ```
  Settings → About phone → Version → Build number
  ```
- **Older OxygenOS**:
  ```
  Settings → About phone → Build number
  ```

**Additional OnePlus Steps:**
- OnePlus devices may require you to **restart** after enabling Developer options
- **"Developer options"** appears under **Settings → System → Developer options**
- Some OnePlus devices have additional security prompts

---

### Xiaomi/MIUI

**Build Number Location:**
- **MIUI 12+**:
  ```
  Settings → About phone → All specs → Build number
  ```
- **MIUI 11**:
  ```
  Settings → About phone → MIUI version (tap 7 times instead of build number)
  ```
- **Older MIUI**:
  ```
  Settings → About phone → MIUI version
  ```

**Optional Xiaomi Steps:**
- **Disable MIUI Optimizations** (for better ADB functionality):
    - In Developer options, find **"Turn off MIUI optimization"**
    - Toggle it **OFF** and restart your device

---

### Huawei/Honor

**Build Number Location:**
- **EMUI 10+**:
  ```
  Settings → About phone → Build number
  ```
- **EMUI 9**:
  ```
  Settings → System → About phone → Build number
  ```
- **Older EMUI**:
  ```
  Settings → About phone → Build number
  ```

**Additional Huawei/Honor Steps:**
- Huawei devices usually have strict security measures
- After enabling Developer options:
    - **"Developer options"** appears under **Settings → System → Developer options**

---

### Oppo

**Build Number Location:**
- **ColorOS 12+**:
  ```
  Settings → About device → Version → Build number
  ```
- **ColorOS 11**:
  ```
  Settings → About phone → Version → Build number
  ```
- **Older ColorOS**:
  ```
  Settings → About phone → Build number
  ```

**Additional Oppo Steps:**
- Oppo devices require additional verification steps
- After enabling Developer options:
    - **"Developer options"** appears under **Settings → Additional settings → Developer options**
    - Enable **"USB debugging"**

**Oppo-Specific Requirements:**
- You may need to be logged into your **Oppo account**
- Some features require **account verification** similar to Xiaomi

---

### Vivo

**Build Number Location:**
- **Funtouch OS 12+**:
  ```
  Settings → About phone → Software version → Build number
  ```
- **Funtouch OS 11**:
  ```
  Settings → About phone → More parameters → Build number
  ```
- **Older Funtouch**:
  ```
  Settings → About phone → Build number
  ```

**Additional Vivo Steps:**
- Vivo devices have similar restrictions to Oppo
- After enabling Developer options:
    - **"Developer options"** appears under **Settings → System → Developer options**

**Vivo-Specific Requirements:**
- **Vivo Account Verification**:
    - Login to your Vivo account may be required
    - Some security features require account verification

---

### Sony

**Build Number Location:**
- **Android 10+**:
  ```
  Settings → About phone → Build number
  ```
- **Android 8-9**:
  ```
  Settings → System → About phone → Build number
  ```
- **Older Android**:
  ```
  Settings → About phone → Build number
  ```

**Additional Sony Steps:**
- Sony devices typically follow **stock Android** closely
- **"Developer options"** appears under **Settings → System → Developer options**
- Sony devices generally have **fewer manufacturer restrictions**

---

### LG

**Build Number Location:**
- **LG UX 9+**:
  ```
  Settings → General → About phone → Software info → Build number
  ```
- **LG UX 8**:
  ```
  Settings → About phone → Software info → Build number
  ```
- **Older LG UX**:
  ```
  Settings → About phone → Build number
  ```

**Additional LG Steps:**
- LG devices may require **restart** after enabling Developer options
- **"Developer options"** appears under **Settings → General → Developer options**
- Some LG devices have additional security prompts

---

### Motorola

**Build Number Location:**
- **Android 10+**:
  ```
  Settings → About phone → Build number
  ```
- **Android 8-9**:
  ```
  Settings → System → About phone → Build number
  ```
- **Older Android**:
  ```
  Settings → About phone → Build number
  ```

**Additional Motorola Steps:**
- Motorola devices typically follow **stock Android**
- **"Developer options"** appears under **Settings → System → Developer options**
- **Minimal manufacturer restrictions** typically apply

---

## Troubleshooting

### Common Issues and Solutions

| Issue                                  | Solution                                                                                                               |
|----------------------------------------|------------------------------------------------------------------------------------------------------------------------|
| **"Developer options" doesn't appear** | Try restarting your phone, then check Settings again<br>Look under "System", "Additional settings", or "Advanced"      |
| **Computer doesn't recognize device**  | Install manufacturer-specific USB drivers<br>Try different USB cables and ports<br>Google: "[device name] USB drivers" |

### Advanced Troubleshooting

**For Huawei/Honor devices:**
- Disable protected apps feature
- Check if HMS Core is interfering

**For Oppo/Vivo devices:**
- Verify account login status
- Disable aggressive battery optimization
- Check auto-start management settings
