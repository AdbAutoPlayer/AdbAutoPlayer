; Kill the app's own adb server before installation so the installer can overwrite
; AdbWinApi.dll and other ADB DLLs that are locked while adb-server is active.
; Only targets the bundled adb.exe in the install directory — does not kill
; system-wide adb processes (e.g. from Android Studio).
; See: https://github.com/AdbAutoPlayer/AdbAutoPlayer/issues/714
!macro NSIS_HOOK_PREINSTALL
  IfFileExists "$INSTDIR\binaries\adb.exe" +1 +2
    nsExec::Exec '"$INSTDIR\binaries\adb.exe" kill-server'
!macroend

!macro NSIS_HOOK_POSTINSTALL
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  IfFileExists "$INSTDIR\binaries\adb.exe" +1 +2
    nsExec::Exec '"$INSTDIR\binaries\adb.exe" kill-server'
!macroend

!macro NSIS_HOOK_POSTUNINSTALL
!macroend
