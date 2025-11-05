from time import sleep

from adb_auto_player.device.adb import InputDevice


class XiaomiInput(InputDevice):
    """Class to interact with Xiaomi Input.

    Note:   it is very likely a generic Keyboard Class can be made that derives
            necessary data during runtime

    ___
    shell getevent -p /dev/input/eventX
    name:   "Xiaomi Input"
    events:
        KEY (0001): 0001  0002  0003  0004  0005  0006  0007  0008
                    0009  000a  000b  000c  000d  000e  000f  0010
                    0011  0012  0013  0014  0015  0016  0017  0018
                    0019  001a  001b  001c  001d  001e  001f  0020
                    0021  0022  0023  0024  0025  0026  0027  0028
                    0029  002a  002b  002c  002d  002e  002f  0030
                    0031  0032  0033  0034  0035  0036  0037  0038
                    0039  003a  003b  003c  003d  003e  003f  0040
                    0041  0042  0043  0044  0045  0046  0047  0048
                    0049  004a  004b  004c  004d  004e  004f  0050
                    0051  0052  0053  0054  0055  0056  0057  0058
                    0059  005a  005b  005c  005d  005e  005f  0060
                    0061  0062  0063  0064  0065  0066  0067  0068
                    0069  006a  006b  006c  006d  006e  006f  0070
                    0071  0072  0073  0074  0075  0076  0077  0078
                    0079  007a  007b  007c  007d  007e  007f  0080
                    0081  0082  0083  0084  0085  0086  0087  0088
                    0089  008a  008b  008c  008d  008e  008f  0090
                    0091  0092  0093  0094  0095  0096  0097  0098
                    0099  009a  009b  009c  009d  009e  009f  00a0
                    00a1  00a2  00a3  00a4  00a5  00a6  00a7  00a8
                    00a9  00aa  00ab  00ac  00ad  00ae  00af  00b0
                    00b1  00b2  00b3  00b4  00b5  00b6  00b7  00b8
                    00b9  00ba  00bb  00bc  00bd  00be  00bf  00c0
                    00c1  00c2  00c3  00c4  00c5  00c6  00c7  00c8
                    00c9  00ca  00cb  00cc  00cd  00ce  00cf  00d0
                    00d1  00d2  00d3  00d4  00d5  00d6  00d7  00d8
                    00d9  00da  00db  00dc  00dd  00de  00df  00e0
                    00e1  00e2  00e3  00e4  00e5  00e6  00e7  00e8
                    00e9  00ea  00eb  00ec  00ed  00ee  00ef  00f0
                    00f1  00f2  00f3  00f4  00f5  00f6  00f7  00f8
                    00f9  00fa  00fb  00fc  00fd  00fe  00ff  0110
                    0111  0112  0113  0114  0115  0116  0117  0145
                    014a* 0244
        REL (0002): 0000  0001  0006  0008
        ABS (0003): 002f  : value 1, min 0, max 31, fuzz 0, flat 0, resolution 0
                    0035  : value 0, min 0, max 1080, fuzz 0, flat 0, resolution 0
                    0036  : value 0, min 0, max 1920, fuzz 0, flat 0, resolution 0
                    0039  : value 0, min 0, max 65535, fuzz 0, flat 0, resolution 0
                    003a  : value 0, min 0, max 0, fuzz 0, flat 0, resolution 0
    input props:
        INPUT_PROP_DIRECT
    """

    EV_KEY = 0x01

    @property
    def name(self) -> str:
        """Name of the input device."""
        return "Xiaomi Input"

    def key_down(self, keycode: int) -> None:
        """Key down event."""
        self.sendevent(self.EV_KEY, keycode, 1)
        self.ev_syn()

    def key_up(self, keycode: int) -> None:
        """Key up event."""
        self.sendevent(self.EV_KEY, keycode, 0)
        self.ev_syn()

    def key_press(self, keycode: int, duration: float = 0.1) -> None:
        """Key down for duration then release."""
        self.key_down(keycode)
        sleep(duration)
        self.key_up(keycode)

    @staticmethod
    def keycode(key: str | int) -> int:
        """Return the keycode for a given key.

        Args:
            key (str | int): The key to lookup. Can be a string or integer.

        Returns:
            int: The corresponding keycode.

        Raises:
            KeyError: If the key is not found in the input event codes.
        """
        codes = XiaomiInput.get_input_event_codes()

        if isinstance(key, int):
            key_str = str(key)
        else:
            key_str = key.upper()

        if key_str in codes:
            return codes[key_str]

        raise KeyError(f"Key '{key_str}' not found in input event codes.")

    @staticmethod
    def get_input_event_codes() -> dict[str, int]:
        """Input event codes.

        https://raw.githubusercontent.com/torvalds/linux/master/include/uapi/linux/input-event-codes.h
        """
        return {
            "ESC": 0x01,
            "1": 0x02,
            "2": 0x03,
            "3": 0x04,
            "4": 0x05,
            "5": 0x06,
            "6": 0x07,
            "7": 0x08,
            "8": 0x09,
            "9": 0x0A,
            "0": 0x0B,
            "MINUS": 0x0C,
            "EQUAL": 0x0D,
            "BACKSPACE": 0x0E,
            "TAB": 0x0F,
            "Q": 0x10,
            "W": 0x11,
            "E": 0x12,
            "R": 0x13,
            "T": 0x14,
            "Y": 0x15,
            "U": 0x16,
            "I": 0x17,
            "O": 0x18,
            "P": 0x19,
            "LEFTBRACE": 0x1A,
            "RIGHTBRACE": 0x1B,
            "ENTER": 0x1C,
            "LEFTCTRL": 0x1D,
            "A": 0x1E,
            "S": 0x1F,
            "D": 0x20,
            "F": 0x21,
            "G": 0x22,
            "H": 0x23,
            "J": 0x24,
            "K": 0x25,
            "L": 0x26,
            "SEMICOLON": 0x27,
            "APOSTROPHE": 0x28,
            "GRAVE": 0x29,
            "LEFTSHIFT": 0x2A,
            "BACKSLASH": 0x2B,
            "Z": 0x2C,
            "X": 0x2D,
            "C": 0x2E,
            "V": 0x2F,
            "B": 0x30,
            "N": 0x31,
            "M": 0x32,
            "COMMA": 0x33,
            "DOT": 0x34,
            "SLASH": 0x35,
            "RIGHTSHIFT": 0x36,
            "KPASTERISK": 0x37,
            "LEFTALT": 0x38,
            "SPACE": 0x39,
            "CAPSLOCK": 0x3A,
            "F1": 0x3B,
            "F2": 0x3C,
            "F3": 0x3D,
            "F4": 0x3E,
            "F5": 0x3F,
            "F6": 0x40,
            "F7": 0x41,
            "F8": 0x42,
            "F9": 0x43,
            "F10": 0x44,
            "NUMLOCK": 0x45,
            "SCROLLLOCK": 0x46,
            "KP7": 0x47,
            "KP8": 0x48,
            "KP9": 0x49,
            "KPMINUS": 0x4A,
            "KP4": 0x4B,
            "KP5": 0x4C,
            "KP6": 0x4D,
            "KPPLUS": 0x4E,
            "KP1": 0x4F,
            "KP2": 0x50,
            "KP3": 0x51,
            "KP0": 0x52,
            "KPDOT": 0x53,
            # undefined: 0x54
            "ZENKAKUHANKAKU": 0x55,
            "102ND": 0x56,
            "F11": 0x57,
            "F12": 0x58,
            "RO": 0x59,
            "KATAKANA": 0x5A,
            "HIRAGANA": 0x5B,
            "HENKAN": 0x5C,
            "KATAKANAHIRAGANA": 0x5D,
            "MUHENKAN": 0x5E,
            "KPJCOMMA": 0x5F,
            "KPENTER": 0x60,
            "RIGHTCTRL": 0x61,
            "KPSLASH": 0x62,
            "SYSRQ": 0x63,
            "RIGHTALT": 0x64,
            "LINEFEED": 0x65,
            "HOME": 0x66,
            "UP": 0x67,
            "PAGEUP": 0x68,
            "LEFT": 0x69,
            "RIGHT": 0x6A,
            "END": 0x6B,
            "DOWN": 0x6C,
            "PAGEDOWN": 0x6D,
            "INSERT": 0x6E,
            "DELETE": 0x6F,
            "MACRO": 0x70,
            "MUTE": 0x71,
            "VOLUMEDOWN": 0x72,
            "VOLUMEUP": 0x73,
            "POWER": 0x74,  # SC System Power Down
            "KPEQUAL": 0x75,
            "KPPLUSMINUS": 0x76,
            "PAUSE": 0x77,
            "SCALE": 0x78,  # AL Compiz Scale (Expose)
            "KPCOMMA": 0x79,
            "HANGEUL": 0x7A,
            "HANJA": 0x7B,
            "YEN": 0x7C,
            "LEFTMETA": 0x7D,
            "RIGHTMETA": 0x7E,
            "COMPOSE": 0x7F,
            "STOP": 0x80,  # AC Stop
            "AGAIN": 0x81,
            "PROPS": 0x82,  # AC Properties
            "UNDO": 0x83,  # AC Undo
            "FRONT": 0x84,
            "COPY": 0x85,  # AC Copy
            "OPEN": 0x86,  # AC Open
            "PASTE": 0x87,  # AC Paste
            "FIND": 0x88,  # AC Search
            "CUT": 0x89,  # AC Cut
            "HELP": 0x8A,  # AL Integrated Help Center
            "MENU": 0x8B,  # Menu (show menu)
            "CALC": 0x8C,  # AL Calculator
            "SETUP": 0x8D,
            "SLEEP": 0x8E,  # SC System Sleep
            "WAKEUP": 0x8F,  # System Wake Up
            "FILE": 0x90,  # AL Local Machine Browser
            "SENDFILE": 0x91,
            "DELETEFILE": 0x92,
            "XFER": 0x93,
            "PROG1": 0x94,
            "PROG2": 0x95,
            "WWW": 0x96,  # AL Internet Browser
            "MSDOS": 0x97,
            "COFFEE": 0x98,  # AL Terminal Lock/Screensaver
            "ROTATE_DISPLAY": 0x99,
            "CYCLEWINDOWS": 0x9A,
            "MAIL": 0x9B,
            "BOOKMARKS": 0x9C,  # AC Bookmarks
            "COMPUTER": 0x9D,
            "BACK": 0x9E,  # AC Back
            "FORWARD": 0x9F,  # AC Forward
            "CLOSECD": 0xA0,
            "EJECTCD": 0xA1,
            "EJECTCLOSECD": 0xA2,
            "NEXTSONG": 0xA3,
            "PLAYPAUSE": 0xA4,
            "PREVIOUSSONG": 0xA5,
            "STOPCD": 0xA6,
            "RECORD": 0xA7,
            "REWIND": 0xA8,
            "PHONE": 0xA9,  # Media Select Telephone
            "ISO": 0xAA,
            "CONFIG": 0xAB,  # AL Consumer Control Configuration
            "HOMEPAGE": 0xAC,  # AC Home
            "REFRESH": 0xAD,  # AC Refresh
            "EXIT": 0xAE,  # AC Exit
            "MOVE": 0xAF,
            "EDIT": 0xB0,
            "SCROLLUP": 0xB1,
            "SCROLLDOWN": 0xB2,
            "KPLEFTPAREN": 0xB3,
            "KPRIGHTPAREN": 0xB4,
            "NEW": 0xB5,  # AC New
            "REDO": 0xB6,  # AC Redo/Repeat
            "F13": 0xB7,
            "F14": 0xB8,
            "F15": 0xB9,
            "F16": 0xBA,
            "F17": 0xBB,
            "F18": 0xBC,
            "F19": 0xBD,
            "F20": 0xBE,
            "F21": 0xBF,
            "F22": 0xC0,
            "F23": 0xC1,
            "F24": 0xC2,
            # undefined: 0xc3  0xc4  0xc5  0xc6  0xc7
            "PLAYCD": 0xC8,
            "PAUSECD": 0xC9,
            "PROG3": 0xCA,
            "PROG4": 0xCB,
            "ALL_APPLICATIONS": 0xCC,  # AC Desktop Show All Applications
            "SUSPEND": 0xCD,
            "CLOSE": 0xCE,  # AC Close
            "PLAY": 0xCF,
            "FASTFORWARD": 0xD0,
            "BASSBOOST": 0xD1,
            "PRINT": 0xD2,  # AC Print
            "HP": 0xD3,
            "CAMERA": 0xD4,
            "SOUND": 0xD5,
            "QUESTION": 0xD6,
            "EMAIL": 0xD7,
            "CHAT": 0xD8,
            "SEARCH": 0xD9,
            "CONNECT": 0xDA,
            "FINANCE": 0xDB,  # AL Checkbook/Finance
            "SPORT": 0xDC,
            "SHOP": 0xDD,
            "ALTERASE": 0xDE,
            "CANCEL": 0xDF,  # AC Cancel
            "BRIGHTNESSDOWN": 0xE0,
            "BRIGHTNESSUP": 0xE1,
            "MEDIA": 0xE2,
            "SWITCHVIDEOMODE": 0xE3,  # Cycle between available video
            "KBDILLUMTOGGLE": 0xE4,
            "KBDILLUMDOWN": 0xE5,
            "KBDILLUMUP": 0xE6,
            "SEND": 0xE7,  # AC Send
            "REPLY": 0xE8,  # AC Reply
            "FORWARDMAIL": 0xE9,  # AC Forward Msg
            "SAVE": 0xEA,  # AC Save
            "DOCUMENTS": 0xEB,
            "BATTERY": 0xEC,
            "BLUETOOTH": 0xED,
            "WLAN": 0xEE,
            "UWB": 0xEF,
            "UNKNOWN": 0xF0,
            "VIDEO_NEXT": 0xF1,  # drive next video source
            "VIDEO_PREV": 0xF2,  # drive previous video source
            "BRIGHTNESS_CYCLE": 0xF3,  # brightness up, after max is min
            "BRIGHTNESS_AUTO": 0xF4,  # Set Auto Brightness
            "DISPLAY_OFF": 0xF5,  # display device to off state
            "WWAN": 0xF6,
            "RFKILL": 0xF7,
            "MICMUTE": 0xF8,
            # undefined: 0xf9  0xfa  0xfb  0xfc  0xfd  0xfe  0xff
            "BTN_MOUSE": 0x110,
            "BTN_LEFT": 0x110,
            "BTN_RIGHT": 0x111,
            "BTN_MIDDLE": 0x112,
            "BTN_SIDE": 0x113,
            "BTN_EXTRA": 0x114,
            "BTN_FORWARD": 0x115,
            "BTN_BACK": 0x116,
            "BTN_TASK": 0x117,
            "BTN_TOOL_FINGER": 0x145,
            # undefined: 014a*
            "APPSELECT": 0x244,
        }
