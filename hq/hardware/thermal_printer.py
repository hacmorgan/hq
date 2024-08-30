"""
Interface with a thermal printer
"""

from typing import Literal
from os import environ

from escpos.printer import Usb
from hq.shell import sh_run


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
            printer.barcode(code=content, bc="UPC-A")

        case _:
            raise NotImplementedError(f"Unsupported content type: {method}")

    # Cut and feed
    printer.cut()


def print_thermally_unpriveliged(
    content: str, method: ThermalPrintMethod = "text"
) -> None:
    """
    Print stuff on a thermal printer from an unpriveliged Python session of a user with
    sudo priveliges

    We use a hacky method to import and run the standard `print_thermally` function with
    sudo

    Args:
        content: Text to print
        method: Method of encoding data
    """
    sh_run(
        "".join(
            [
                f"source {environ['VIRTUAL_ENV']}/bin/activate && ",
                "sudo python3 -c 'from hq.hardware.thermal_printer import print_thermally;",
                f'print_thermally(content="{content}", method="{method}")\'',
            ]
        )
    )
