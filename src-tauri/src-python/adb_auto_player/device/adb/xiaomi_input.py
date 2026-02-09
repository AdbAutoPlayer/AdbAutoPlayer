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
