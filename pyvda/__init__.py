"""
Python Virtual Desktop Accessor
================================

Implements a subset of the functionality offered by https://github.com/Ciantic/VirtualDesktopAccessor, written in pure Python and installable via pip.

Installation
-------------
.. code:: shell

    $ pip install pyvda

Example
-------
.. code:: python

    from pyvda import AppView, get_apps_by_z_order, VirtualDesktop, get_virtual_desktops

    number_of_active_desktops = len(get_virtual_desktops())
    print(f"There are {number_of_active_desktops} active desktops")

    current_desktop = VirtualDesktop.current()
    print(f"Current desktop is number {current_desktop}")

    current_window = AppView.current()
    target_desktop = VirtualDesktop(5)
    current_window.move(target_desktop)
    print(f"Moved window {current_window.hwnd} to {target_desktop.number}")

    print("Going to desktop number 5")
    VirtualDesktop(5).go()

    print("Pinning the current window")
    AppView.current().pin()
"""

import os
import platform


def _check_release():
    try:
        release = int(platform.release())
        return release >= 10
    except ValueError:
        return platform.release() == "10"

def _check_version():
    if platform.system() != "Windows" or not _check_release():
        raise NotImplementedError(
            "The virtual desktop feature is only available on Windows 10 and later."
        )

if not os.getenv("READTHEDOCS"):
    _check_version()

from ._version import __version__
from .pyvda import (
    AppView,
    VirtualDesktop,
    get_apps_by_z_order,
    get_virtual_desktops,
    set_wallpaper_for_all_desktops,
)
from .notification import VirtualDesktopNotificationService
