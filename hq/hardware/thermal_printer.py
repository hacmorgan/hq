"""
Interface with a thermal printer
"""

from typing import Literal

from escpos.printer import Usb


ThermalPrintMethod = Literal["text", "barcode", "qr", "image"]


def print_thermally(content: str, method: ThermalPrintMethod = "text") -> None:
    """
    Print stuff on a thermal printer

    Args:
        content: Text to print
        method: Method of encoding data
    """
    # Initialise printer
    printer = Usb(idVendor=0x04B8, idProduct=0x0E02, profile="TM-T88V")

    match method:

        case "text":
            printer.set(smooth=True)
            printer.text(content)

        case "qr":
            printer.qr(content)

        case "barcode":
            printer.barcode(content)

        case _:
            raise NotImplementedError(f"Unsupported content type: {method}")

    # Cut and feed
    printer.cut()
