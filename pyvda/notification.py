"""
Virtual Desktop Notification Support
=====================================

Provides COM-based event notifications for virtual desktop changes.

Usage
-----
.. code:: python

    from pyvda.notification import VirtualDesktopNotificationService

    service = VirtualDesktopNotificationService()

    class MyHandler:
        def desktop_changed(self, *args):
            print("Desktop changed!")
        def desktop_created(self, *args):
            print("Desktop created!")
        def desktop_destroyed(self, *args):
            print("Desktop destroyed!")

    cookie = service.register(MyHandler())
    # ... later ...
    service.unregister(cookie)
"""

import ctypes
import logging
from ctypes import POINTER, c_void_p

import comtypes

from pyvda.com_base import IServiceProvider
from pyvda.com_defns import (
    CLSID_ImmersiveShell,
    IVirtualDesktopNotification,
    IVirtualDesktopNotificationService,
)
from pyvda.const import CLSID_IVirtualNotificationService

logger = logging.getLogger(__name__)


class DesktopNotificationSink(comtypes.COMObject):
    """comtypes COMObject implementing IVirtualDesktopNotification.

    Delegates each callback to a user-supplied handler object.
    Only methods that exist on the handler are called — missing ones
    are silently ignored (return S_OK).
    """

    _com_interfaces_ = [IVirtualDesktopNotification]

    def __init__(self, handler=None):
        super().__init__()
        self._handler = handler

    def _dispatch(self, method_name, *args):
        if self._handler is not None:
            fn = getattr(self._handler, method_name, None)
            if fn is not None:
                try:
                    fn(*args)
                except Exception:
                    logger.exception("Error in notification handler %s", method_name)
        return 0

    def VirtualDesktopCreated(self, *args):
        return self._dispatch("desktop_created", *args)

    def VirtualDesktopDestroyBegin(self, *args):
        return self._dispatch("desktop_destroy_begin", *args)

    def VirtualDesktopDestroyFailed(self, *args):
        return self._dispatch("desktop_destroy_failed", *args)

    def VirtualDesktopDestroyed(self, *args):
        return self._dispatch("desktop_destroyed", *args)

    def VirtualDesktopMoved(self, *args):
        return self._dispatch("desktop_moved", *args)

    def VirtualDesktopRenamed(self, *args):
        return self._dispatch("desktop_renamed", *args)

    def ViewVirtualDesktopChanged(self, *args):
        return self._dispatch("view_changed", *args)

    def CurrentVirtualDesktopChanged(self, *args):
        return self._dispatch("desktop_changed", *args)

    def VirtualDesktopWallpaperChanged(self, *args):
        return self._dispatch("desktop_wallpaper_changed", *args)

    def VirtualDesktopSwitched(self, *args):
        return self._dispatch("desktop_switched", *args)

    def RemoteVirtualDesktopConnected(self, *args):
        return self._dispatch("remote_desktop_connected", *args)

    def Proc7(self, *args):
        return 0


class VirtualDesktopNotificationService:
    """High-level wrapper for IVirtualDesktopNotificationService.

    Handles COM service acquisition, sink creation, and registration.
    """

    def __init__(self):
        self._service = None
        self._sinks: dict[int, DesktopNotificationSink] = {}
        self._acquire_service()

    @staticmethod
    def _try_init_com():
        try:
            comtypes.CoInitializeEx()
        except OSError:
            pass

    def _acquire_service(self):
        self._try_init_com()
        pServiceProvider = comtypes.CoCreateInstance(
            CLSID_ImmersiveShell,
            IServiceProvider,
            comtypes.CLSCTX_LOCAL_SERVER,
        )
        pNotifService = POINTER(IVirtualDesktopNotificationService)()
        pServiceProvider.QueryService(
            CLSID_IVirtualNotificationService,
            IVirtualDesktopNotificationService._iid_,
            pNotifService,
        )
        self._service = pNotifService

    def register(self, handler=None) -> int:
        """Register a notification handler and return an integer cookie.

        Parameters
        ----------
        handler : object, optional
            An object with any of these optional methods:
            ``desktop_changed``, ``desktop_created``, ``desktop_destroyed``,
            ``desktop_destroy_begin``, ``desktop_destroy_failed``,
            ``desktop_moved``, ``desktop_renamed``, ``view_changed``,
            ``desktop_wallpaper_changed``, ``desktop_switched``,
            ``remote_desktop_connected``.

            If None, a no-op sink is registered (useful for keeping COM alive).
        """
        sink = DesktopNotificationSink(handler)
        raw_ptr = ctypes.cast(
            sink._com_pointers_[IVirtualDesktopNotification._iid_],
            c_void_p,
        )
        cookie = self._service.Register(raw_ptr)
        self._sinks[cookie] = sink  # prevent GC
        logger.info("Registered desktop notification (cookie=%d)", cookie)
        return cookie

    def unregister(self, cookie: int):
        """Unregister a previously registered notification handler."""
        self._service.Unregister(cookie)
        self._sinks.pop(cookie, None)
        logger.info("Unregistered desktop notification (cookie=%d)", cookie)
