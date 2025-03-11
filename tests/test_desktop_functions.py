import sys
import threading
import time
from typing import Optional

import pytest
import win32gui
from comtypes import COINIT_MULTITHREADED, CoInitializeEx

from pyvda import AppView, VirtualDesktop, get_apps_by_z_order, get_virtual_desktops

current_window = AppView.current()
current_desktop = VirtualDesktop.current()

def test_move_and_go():
    current_window.move(VirtualDesktop(1))

    VirtualDesktop(1).go()
    current_desktop_number = VirtualDesktop.current().number
    assert current_desktop_number == 1, f"Wanted 1, got {current_desktop_number}"

    current_window_desktop_number = current_window.desktop.number
    assert current_window_desktop_number == 1, f"Wanted 1, got {current_window_desktop_number}"

    current_window.move(current_desktop)
    current_desktop.go()

def test_pin_app():
    assert not current_window.is_app_pinned()
    current_window.pin_app()
    assert current_window.is_app_pinned()
    current_window.unpin_app()
    assert not current_window.is_app_pinned()

def test_pin_window():
    assert not current_window.is_pinned()
    current_window.pin()
    assert current_window.is_pinned()
    current_window.unpin()
    assert not current_window.is_pinned()

def test_z_order():
    apps = get_apps_by_z_order()
    assert apps[0] == AppView.current()

    assert len(get_apps_by_z_order(False, False)) > len(apps)

def test_switch_focus():
    apps = get_apps_by_z_order()
    if len(apps) == 1:
        raise Exception("For testing purposes, open another window!")

    ts = apps[0].get_activation_timestamp()

    apps[1].set_focus()
    time.sleep(1)
    assert AppView.current() == apps[1]
    apps[0].switch_to()
    time.sleep(1)
    assert AppView.current() == apps[0]

    assert apps[0].get_activation_timestamp() > ts

def test_visibility():
    cur = AppView.current()
    assert cur.is_shown_in_switchers()
    assert cur.is_visible()

def test_current():
    count = len(get_virtual_desktops())
    current = VirtualDesktop.current().number
    assert 0 < current <= count, f"Current desktop number {current} is outside of expected range 0-{count}"

    hwnd = win32gui.GetForegroundWindow()
    assert AppView(hwnd) == AppView.current()
    assert AppView(hwnd).is_on_current_desktop()

def test_create_and_remove_desktop():
    old_count = len(get_virtual_desktops())
    new = VirtualDesktop.create()
    new_count = len(get_virtual_desktops())
    expected_count = old_count + 1
    assert new_count == expected_count, f"Wanted {expected_count}, got {new_count}"
    new.go()

    new.remove(fallback=VirtualDesktop(1))
    new_count = len(get_virtual_desktops())
    assert new_count == old_count, f"Wanted {new_count}, got {new_count}"
    fallback = VirtualDesktop.current().number
    assert fallback == 1, f"Wanted 1, got {fallback}"

    time.sleep(1) # Got to wait for the animation before we can return
    current_desktop.go()
    current_window.set_focus()


@pytest.mark.xfail(
    condition=not sys.getwindowsversion().build >= 19041,
    reason="<=18363 has no IVirtualDesktopManagerInternal2 manager",
    raises=NotImplementedError,
    strict=True
)
def test_desktop_names():
    current_name = current_desktop.name
    test_name = "pyvda testing"
    current_desktop.rename(test_name)
    assert current_desktop.name == test_name, f"Wanted '{test_name}', got '{current_desktop.name}'"
    current_desktop.rename(current_name)
    assert current_desktop.name == current_name, f"Wanted '{current_name}', got '{current_desktop.name}'"

@pytest.mark.skipif(sys.getwindowsversion().build >= 19041, reason="Only for builds <=19041")
def test_desktop_names_pre_19041():
    re_is_not_supported = r".* is not supported .*"

    with pytest.raises(NotImplementedError, match=re_is_not_supported):
        current_desktop.name

    with pytest.raises(NotImplementedError, match=re_is_not_supported):
        current_desktop.rename("Won't work")


def test_move_and_go_threads():
    error: Optional[Exception] = None
    def f():
        nonlocal error
        try:
            test_move_and_go()
        except Exception as e:
            error = e
    t = threading.Thread(target=f)
    t.start()
    t.join()
    if error is not None:
        raise error

def test_initialisation_with_com_mta():
    error: Optional[Exception] = None
    def f():
        nonlocal error
        try:
            CoInitializeEx(COINIT_MULTITHREADED)
            test_move_and_go()
        except Exception as e:
            error = e
    t = threading.Thread(target=f)
    t.start()
    t.join()
    if error is not None:
        raise error
