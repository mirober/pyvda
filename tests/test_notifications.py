import ctypes
import ctypes.wintypes
import threading
import time

import pytest
from comtypes import COINIT_MULTITHREADED, CoInitializeEx

from pyvda import VirtualDesktop, VirtualDesktopNotificationService, get_virtual_desktops


def _pump_messages(event, timeout=5):
    """Pump Windows messages until *event* is set or *timeout* seconds elapse.

    COM STA callbacks are dispatched via the Windows message queue, so a
    message pump is required in non-GUI processes like pytest."""
    user32 = ctypes.windll.user32
    msg = ctypes.wintypes.MSG()
    deadline = time.monotonic() + timeout
    while not event.is_set() and time.monotonic() < deadline:
        while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        time.sleep(0.01)


def test_register_unregister():
    """Basic registration and unregistration should succeed."""
    svc = VirtualDesktopNotificationService()
    cookie = svc.register()
    assert isinstance(cookie, int)
    svc.unregister(cookie)


def test_register_with_handler():
    """Registration with a handler object should succeed."""
    class Handler:
        pass

    svc = VirtualDesktopNotificationService()
    cookie = svc.register(Handler())
    svc.unregister(cookie)


def test_multiple_registrations():
    """Multiple handlers can be registered and unregistered independently."""
    svc = VirtualDesktopNotificationService()
    cookie1 = svc.register()
    cookie2 = svc.register()
    assert cookie1 != cookie2
    svc.unregister(cookie1)
    svc.unregister(cookie2)


def test_desktop_changed_callback():
    """Switching desktops should trigger the desktop_changed callback."""
    if len(get_virtual_desktops()) < 2:
        pytest.skip("Need at least 2 desktops to test switching")

    event = threading.Event()
    original = VirtualDesktop.current()

    class Handler:
        def desktop_changed(self, *args):
            event.set()

    svc = VirtualDesktopNotificationService()
    cookie = svc.register(Handler())
    try:
        target = VirtualDesktop(2) if original.number == 1 else VirtualDesktop(1)
        target.go()
        _pump_messages(event, timeout=5)
        assert event.is_set(), "desktop_changed callback was not fired"
    finally:
        original.go()
        time.sleep(0.5)
        svc.unregister(cookie)


def test_desktop_created_destroyed_callback():
    """Creating and destroying a desktop should trigger callbacks."""
    created_event = threading.Event()
    destroyed_event = threading.Event()

    class Handler:
        def desktop_created(self, *args):
            created_event.set()

        def desktop_destroyed(self, *args):
            destroyed_event.set()

    svc = VirtualDesktopNotificationService()
    cookie = svc.register(Handler())
    try:
        new_desktop = VirtualDesktop.create()
        _pump_messages(created_event, timeout=5)
        assert created_event.is_set(), "desktop_created callback was not fired"

        new_desktop.remove(fallback=VirtualDesktop(1))
        _pump_messages(destroyed_event, timeout=5)
        assert destroyed_event.is_set(), "desktop_destroyed callback was not fired"
        time.sleep(1)  # Wait for animation
    finally:
        svc.unregister(cookie)


def test_register_unregister_from_thread():
    """Registration should work from a non-main thread."""
    error = None

    def f():
        nonlocal error
        try:
            CoInitializeEx(COINIT_MULTITHREADED)
            svc = VirtualDesktopNotificationService()
            cookie = svc.register()
            svc.unregister(cookie)
        except Exception as e:
            error = e

    t = threading.Thread(target=f)
    t.start()
    t.join()
    if error is not None:
        raise error
