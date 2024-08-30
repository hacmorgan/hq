"""
Interface with a thermal printer
"""


from typing import Literal

from escpos.printer.usb import Usb


ThermalPrintMethod = Literal["text", "barcode", "qr", "image"]


def print_thermally(content: str, method: ThermalPrintMethod = "text") -> None:
    """
    Print stuff on a thermal printer

    Args:
        content: Text to print
        method: Method of encoding data
    """
    printer = Usb(0, profile="TM-T88V")
    printer.set(
        custom_size=True,
        width=5,
        height=5,
        smooth=True,
    )
    printer.text(content)
    printer.cut()
