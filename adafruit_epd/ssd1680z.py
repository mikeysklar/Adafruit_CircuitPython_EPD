# SPDX-License-Identifier: MIT

"""
`adafruit_epd.ssd1680z` - Adafruit SSD1680Z - ePaper display driver
====================================================================================
CircuitPython driver for Adafruit SSD1680Z display breakouts
* Author(s): Mikey Sklar Melissa LeBlanc-Williams
"""

import time
from micropython import const
import adafruit_framebuf
from adafruit_epd.epd import Adafruit_EPD

try:
    """Needed for type annotations"""
    import typing  # pylint: disable=unused-import
    from busio import SPI
    from digitalio import DigitalInOut

except ImportError:
    pass

__version__ = "2.12.3"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_EPD.git"

_SSD1680Z_DRIVER_CONTROL = const(0x01)
_SSD1680Z_GATE_VOLTAGE = const(0x03)
_SSD1680Z_SOURCE_VOLTAGE = const(0x04)
_SSD1680Z_INIT_SETTING = const(0x08)
_SSD1680Z_INIT_WRITE_REG = const(0x09)
_SSD1680Z_INIT_READ_REG = const(0x0A)
_SSD1680Z_BOOSTER_SOFT_START = const(0x0C)
_SSD1680Z_DEEP_SLEEP = const(0x10)
_SSD1680Z_DATA_MODE = const(0x11)
_SSD1680Z_SW_RESET = const(0x12)
_SSD1680Z_HV_DETECT = const(0x14)
_SSD1680Z_VCI_DETECT = const(0x15)
_SSD1680Z_TEMP_CONTROL = const(0x18)
_SSD1680Z_TEMP_WRITE = const(0x1A)
_SSD1680Z_TEMP_READ = const(0x1B)
_SSD1680Z_EXTTEMP_WRITE = const(0x1C)
_SSD1680Z_MASTER_ACTIVATE = const(0x20)
_SSD1680Z_DISP_CTRL1 = const(0x21)
_SSD1680Z_DISP_CTRL2 = const(0x22)
_SSD1680Z_WRITE_BWRAM = const(0x24)
_SSD1680Z_WRITE_REDRAM = const(0x26)
_SSD1680Z_READ_RAM = const(0x27)
_SSD1680Z_VCOM_SENSE = const(0x28)
_SSD1680Z_VCOM_DURATION = const(0x29)
_SSD1680Z_WRITE_VCOM_OTP = const(0x2A)
_SSD1680Z_WRITE_VCOM_CTRL = const(0x2B)
_SSD1680Z_WRITE_VCOM_REG = const(0x2C)
_SSD1680Z_READ_OTP = const(0x2D)
_SSD1680Z_READ_USERID = const(0x2E)
_SSD1680Z_READ_STATUS = const(0x2F)
_SSD1680Z_WRITE_WS_OTP = const(0x30)
_SSD1680Z_LOAD_WS_OTP = const(0x31)
_SSD1680Z_WRITE_LUT = const(0x32)
_SSD1680Z_CRC_CALC = const(0x34)
_SSD1680Z_CRC_READ = const(0x35)
_SSD1680Z_PROG_OTP = const(0x36)
_SSD1680Z_WRITE_DISPLAY_OPT = const(0x37)
_SSD1680Z_WRITE_USERID = const(0x38)
_SSD1680Z_OTP_PROGMODE = const(0x39)
_SSD1680Z_WRITE_BORDER = const(0x3C)
_SSD1680Z_END_OPTION = const(0x3F)
_SSD1680Z_SET_RAMXPOS = const(0x44)
_SSD1680Z_SET_RAMYPOS = const(0x45)
_SSD1680Z_AUTOWRITE_RED = const(0x46)
_SSD1680Z_AUTOWRITE_BW = const(0x47)
_SSD1680Z_SET_RAMXCOUNT = const(0x4E)
_SSD1680Z_SET_RAMYCOUNT = const(0x4F)
_SSD1680Z_NOP = const(0xFF)


class Adafruit_SSD1680Z(Adafruit_EPD):
    """driver class for Adafruit SSD1680Z ePaper display breakouts"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        width: int,
        height: int,
        spi: SPI,
        *,
        cs_pin: DigitalInOut,
        dc_pin: DigitalInOut,
        sramcs_pin: DigitalInOut,
        rst_pin: DigitalInOut,
        busy_pin: DigitalInOut
    ) -> None:
        super().__init__(
            width, height, spi, cs_pin, dc_pin, sramcs_pin, rst_pin, busy_pin
        )

        stride = width
        if stride % 8 != 0:
            stride += 8 - stride % 8

        self._buffer1_size = int(stride * height / 8)
        self._buffer2_size = self._buffer1_size

        if sramcs_pin:
            self._buffer1 = self.sram.get_view(0)
            self._buffer2 = self.sram.get_view(self._buffer1_size)
        else:
            self._buffer1 = bytearray(self._buffer1_size)
            self._buffer2 = bytearray(self._buffer2_size)

        self._framebuf1 = adafruit_framebuf.FrameBuffer(
            self._buffer1,
            width,
            height,
            stride=stride,
            buf_format=adafruit_framebuf.MHMSB,
        )
        self._framebuf2 = adafruit_framebuf.FrameBuffer(
            self._buffer2,
            width,
            height,
            stride=stride,
            buf_format=adafruit_framebuf.MHMSB,
        )
        self.set_black_buffer(0, True)
        self.set_color_buffer(1, False)
        # pylint: enable=too-many-arguments

    def begin(self, reset: bool = True) -> None:
        """Begin communication with the display and set basic settings"""
        if reset:
            self.hardware_reset()
        self.power_down()

    def busy_wait(self) -> None:
        """Wait for display to be done with current task, either by polling the
        busy pin, or pausing"""
        if self._busy:
            while self._busy.value:
                time.sleep(0.01)
        else:
            time.sleep(0.5)

    def power_up(self) -> None:
        """Power up the display and set basic settings for SSD1680Z"""
        self.hardware_reset()
        self.busy_wait()

        # Send a software reset command
        self.command(_SSD1680Z_SW_RESET)
        self.busy_wait()

        # Driver output control for SSD1680Z
        self.command(
            _SSD1680Z_DRIVER_CONTROL,
            bytearray([self._height - 1, (self._height - 1) >> 8, 0x00]),
        )

        # Set data entry mode
        self.command(_SSD1680Z_DATA_MODE, bytearray([0x03]))  # Increment X and Y

        # Set RAM X and Y start/end positions
        self.command(_SSD1680Z_SET_RAMXPOS, bytearray([0x00, (self._width // 8) - 1]))
        self.command(
            _SSD1680Z_SET_RAMYPOS,
            bytearray([0x00, 0x00, self._height - 1, (self._height - 1) >> 8]),
        )

        # Set RAM X and Y count start
        self.command(_SSD1680Z_SET_RAMXCOUNT, bytearray([0x00]))
        self.command(_SSD1680Z_SET_RAMYCOUNT, bytearray([0x00, 0x00]))

        # Set border waveform control
        self.command(_SSD1680Z_WRITE_BORDER, bytearray([0x80]))

        self.busy_wait()

    def power_down(self) -> None:
        """Power down the display - required when not actively displaying!"""
        self.command(_SSD1680Z_DEEP_SLEEP, bytearray([0x01]))
        time.sleep(0.1)

    def update(self) -> None:
        """Activate display update for SSD1680Z"""
        self.command(_SSD1680Z_DISP_CTRL2, bytearray([0xF7]))  # Full update
        self.command(_SSD1680Z_MASTER_ACTIVATE)
        self.busy_wait()
        if not self._busy:
            time.sleep(3)  # Wait for update to complete

    def write_ram(self, index: int) -> int:
        """Write to RAM for SSD1680Z."""
        if index == 0:
            return self.command(_SSD1680Z_WRITE_BWRAM, end=False)
        if index == 1:
            return self.command(_SSD1680Z_WRITE_REDRAM, end=False)
        raise RuntimeError("RAM index must be 0 or 1")

    def set_ram_address(
        self, x: int, y: int
    ) -> None:  # pylint: disable=unused-argument, no-self-use
        """Set the RAM address location, not used on this chipset but required by
        the superclass"""
        # Set RAM X address counter
        self.command(_SSD1680Z_SET_RAMXCOUNT, bytearray([x + 1]))
        # Set RAM Y address counter
        self.command(_SSD1680Z_SET_RAMYCOUNT, bytearray([y, y >> 8]))
