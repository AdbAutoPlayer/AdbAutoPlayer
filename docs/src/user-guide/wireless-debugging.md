# Wireless Debugging (Real Phone over Wi-Fi)

Run AdbAutoPlayer on a real Android phone **without a USB cable**. The phone and the PC talk over your home network using Android's built-in **Wireless debugging**.

---

## Table of Contents

- [Before You Start](#before-you-start)
- [Step 1: Turn On Wireless Debugging on the Phone](#step-1-turn-on-wireless-debugging-on-the-phone)
- [Step 2: Pair the Phone with AdbAutoPlayer](#step-2-pair-the-phone-with-adbautoplayer)
- [Step 3: Check That It Worked](#step-3-check-that-it-worked)
- [Step 4: Screen Settings for Real Phones](#step-4-screen-settings-for-real-phones)
- [Everyday Use](#everyday-use)
- [Troubleshooting](#troubleshooting)

---

## Before You Start

| Requirement                   | Details                                                                                                                              |
|-------------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| **Android 11 or newer**       | Wireless debugging does not exist on older versions. On Android 10 or older, use the [USB guide](real-phone-guide.md) instead.       |
| **Developer options enabled** | Follow [Step 1 of the Real Phone Guide](real-phone-guide.md#step-1-enable-developer-options) (tap "Build number" 7 times).           |
| **Same network**              | The phone must be on **Wi-Fi**, connected to the **same router** as the PC. The PC itself can use Wi-Fi **or** an Ethernet cable.    |
| **A home/private network**    | Guest networks and public Wi-Fi (hotels, cafés, schools) usually block devices from seeing each other. Use your normal home network. |

> [!NOTE]
> You only need to **pair** once. After that, turning Wireless debugging on is enough.

---

## Step 1: Turn On Wireless Debugging on the Phone

1. Open **Settings** on the phone.
2. Open **Developer options**:
    - **Google Pixel / stock Android:** `Settings → System → Developer options`
    - **Samsung:** `Settings → Developer options` (at the bottom of the list)
    - **Other brands:** see [where Developer options is](real-phone-guide.md#brand-specific-instructions) for your brand
3. Scroll down to the **Debugging** section and tap the words **"Wireless debugging"** (not only the switch).
4. Turn the switch **ON**.
5. The phone asks *"Allow wireless debugging on this network?"*
    - Tick **"Always allow on this network"**
    - Tap **Allow**

You are now on the **Wireless debugging** screen. Near the top it shows **"IP address & Port"**, for example `192.168.1.50:37123`.
**Write this down**: it is your **Device ID**.

---

## Step 2: Pair the Phone with AdbAutoPlayer

### 2.1 Get the pairing code (on the phone)

1. On the **Wireless debugging** screen, tap **"Pair device with pairing code"**.
2. A popup shows:
    - **Wi-Fi pairing code**: 6 digits, e.g. `482915`
    - **IP address & Port**: e.g. `192.168.1.50:41001`

> [!IMPORTANT]
> **Keep this popup open** until pairing is finished. The code and port stop working as soon as the popup closes. Opening it again gives you a **new** code and port.

<!-- -->

> [!WARNING]
> The popup's **IP address & Port** is **not** the same as the one on the main Wireless debugging screen: the IP is the same but the **port is different**.
>
> - Popup (pairing) → goes in **Pairing Address**
> - Main screen (Step 1) → goes in **Device ID**

### 2.2 Enter the details in AdbAutoPlayer (on the PC)

1. Open AdbAutoPlayer and click the **ADB Settings** button (its tooltip reads *ADB Settings*).
2. In the **Device** section:
    - **Device ID**: the address from the **main** Wireless debugging screen (Step 1), e.g. `192.168.1.50:37123`
3. In the **Wireless Debugging** section:
    - **Enable Wireless Debugging (Android 11+)**: turn **ON**
    - **Pairing Address (IP:Port)**: the address from the **popup**, e.g. `192.168.1.50:41001`
    - **Pairing Code**: the 6 digits from the popup, e.g. `482915`
4. Click **Save Settings**.

Within a few seconds AdbAutoPlayer pairs with the phone and connects to it. You don't have to start a task for this.

---

## Step 3: Check That It Worked

You should see all of these:

- **On the phone:** the pairing popup closes by itself, and your PC appears under **"Paired devices"** on the Wireless debugging screen.
- **In the AdbAutoPlayer log:**

  ```text
  Wireless Debugging: paired with 192.168.1.50:41001
  ```

- **In the profile list (left sidebar):** your profile shows the phone's address instead of **"no device"**.

When it works:

1. Open **ADB Settings** again.
2. **Clear** the **Pairing Address** and **Pairing Code** fields (leave **Enable Wireless Debugging** ON).
3. Click **Save Settings**.

Clearing them stops the app from retrying an old, expired code when the phone is off, which would otherwise fill the log with pairing warnings.

---

## Step 4: Screen Settings for Real Phones

The bot is designed for a **1080x1920** portrait screen. Most phones have a different resolution, so in **ADB Settings → Device**:

| Setting                           | What to do                                                                         |
|-----------------------------------|------------------------------------------------------------------------------------|
| **Resize Display (Phone/Tablet)** | Turn **ON**. The bot changes the phone's display size to 1080x1920 when it starts. |
| **Vertical Screen Offset (px)**   | Leave at **0** unless the bot taps in the wrong place (see the warning below).     |

To give the phone its normal resolution back, use the **Reset Display Size** button shown in ADB Settings.

> [!WARNING]
> **Vertical Screen Offset: when taps or text reading are slightly off**
>
> On some phones, after **Resize Display**, the game is drawn a little **higher or lower** than the bot expects. This is usually caused by the status bar, a notch or the camera cutout. When this happens you will notice that:
>
> - taps land **a bit above or below** the button they were meant for;
> - scans (for example guild or hero scans) **miss rows or read the wrong text**.
>
> **Vertical Screen Offset** corrects this. It shifts everything the bot sees and taps by that many pixels:
>
> - **positive** value (e.g. `40`): the game content is **lower** than expected;
> - **negative** value (e.g. `-40`): the game content is **higher** than expected.
>
> **Some AFK Journey scans detect this for you.** If the log shows a message like *"Your device's display may be misaligned — try setting ADB Settings -> Device -> Vertical Screen Offset to approximately 38"*, enter that number and run the scan again.
>
> Otherwise, change it **in small steps** (10–20 px), save, and test again. **Only change it if you see these problems.** A wrong offset makes *every* tap miss. **Emulators should always stay at 0.**

---

## Everyday Use

- **Turn Wireless debugging on** each time you want to use the bot. Many phones switch it **off after a restart** or when you join a different Wi-Fi network. You do **not** need to pair again.
- **The port changes** every time Wireless debugging is turned on, so your saved Device ID gets outdated. With **Enable Wireless Debugging** ON, AdbAutoPlayer finds the new port by itself. The log then shows:

  ```text
  Wireless Debugging: connected to 192.168.1.50:40211. You can set it as Device ID in the ADB Settings.
  ```

  Updating the Device ID is optional, but it makes connecting faster.
- **The Scan button** next to Device ID also finds the phone (with the option ON and saved). It suggests the **first** device found: if an emulator is running too, it may suggest the emulator instead.
- **Keep the phone awake and charging** during long runs. Enable **"Stay awake"** in Developer options, and keep the phone cool (see the [Real Phone Guide](real-phone-guide.md#important-considerations)).

> [!CAUTION]
> Anyone on the same network who has been paired can control the phone while Wireless debugging is on. **Turn it off when you are not using the bot**, and never turn it on over public Wi-Fi.
> To remove the PC, go to **Wireless debugging → Paired devices**, tap the PC, and choose **Forget**.

---

## Troubleshooting

| Problem                                                                    | Solution                                                                                                                                                                                                                                                                                                           |
|----------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **"Wireless debugging" is missing** in Developer options                   | The phone runs Android 10 or older. Use the [USB guide](real-phone-guide.md).                                                                                                                                                                                                                                      |
| The switch turns **off by itself** right after turning it on               | The phone is not on Wi-Fi (mobile data does not work). Connect to Wi-Fi and try again.                                                                                                                                                                                                                             |
| Log: *"pairing with … failed: … protocol fault"* or *"connection refused"* | The pairing popup was closed, so the code expired. Open **"Pair device with pairing code"** again and enter the **new** code **and** port, then save. Leave the popup open.                                                                                                                                        |
| Log: *"pairing with … failed: Wrong password"*                             | The code was mistyped. Use the code currently shown in the popup.                                                                                                                                                                                                                                                  |
| Pairing succeeded but the profile still shows **"no device"**              | Check that **Device ID** holds the address from the **main** Wireless debugging screen, **not** the popup's pairing address.                                                                                                                                                                                       |
| Worked yesterday, **not today**                                            | Turn Wireless debugging back on. Make sure **Enable Wireless Debugging** is ON so the new port is found automatically, or copy the new "IP address & Port" into Device ID.                                                                                                                                         |
| The app **never finds the phone**, and the Scan button finds nothing       | The PC and the phone are probably on different networks: a guest network, a second router or mesh node with its own network, a VPN on the PC, or "AP/client isolation" turned on in the router. Put both on the same home network. As a fallback, copy the phone's "IP address & Port" into **Device ID** by hand. |
| Windows asks whether **adb.exe** may use the network                       | Click **Allow** (tick private networks). If you clicked Cancel before, allow `adb.exe` in *Windows Security → Firewall → Allow an app through firewall*.                                                                                                                                                           |
| Taps are **slightly above/below** the buttons                              | Adjust the [Vertical Screen Offset](#step-4-screen-settings-for-real-phones).                                                                                                                                                                                                                                      |
| The phone disconnects when the screen turns off                            | Enable **"Stay awake"** in Developer options and keep the phone charging. Turn off battery optimisation for Wi-Fi if your phone has that option.                                                                                                                                                                   |

Still stuck? See the general [Troubleshooting](troubleshoot.md) page, then click **Show Debug info** in the app and include the log when asking for help.
