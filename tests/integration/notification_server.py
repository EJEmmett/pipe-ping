# ruff: noqa: N802
"""A /ake ``org.freedesktop.Notifications`` server for integration tests.

Implements the subset of the Desktop Notifications spec that
``desktop-notifier``'s D-Bus backend calls, recording every ``Notify`` so tests
can assert on exactly what a real notification daemon would have received.
"""

from typing import Annotated

from dbus_fast.annotations import (
    DBusDict,
    DBusInt32,
    DBusSignature,
    DBusStr,
    DBusUInt32,
)
from dbus_fast.service import ServiceInterface, dbus_method, dbus_signal

BUS_NAME = "org.freedesktop.Notifications"
OBJECT_PATH = "/org/freedesktop/Notifications"

DBusStrList = Annotated[list[str], DBusSignature("as")]


class FakeNotificationServer(ServiceInterface):
    def __init__(self) -> None:
        super().__init__(BUS_NAME)
        self.notifications: list[dict] = []

    @dbus_method()
    def GetCapabilities(self) -> DBusStrList:
        return ["actions", "body"]

    @dbus_method()
    def GetServerInformation(
        self,
    ) -> Annotated[tuple[str, str, str, str], DBusSignature("ssss")]:
        return ("fake", "pipe-ping", "1.0", "1.2")

    @dbus_method()
    def Notify(
        self,
        app_name: DBusStr,
        replaces_id: DBusUInt32,
        app_icon: DBusStr,
        summary: DBusStr,
        body: DBusStr,
        actions: DBusStrList,
        hints: DBusDict,
        expire_timeout: DBusInt32,
    ) -> DBusUInt32:
        self.notifications.append(
            {
                "app_name": app_name,
                "summary": summary,
                "body": body,
                "actions": actions,
                "hints": {key: variant.value for key, variant in hints.items()},
            }
        )
        return len(self.notifications)

    @dbus_method()
    def CloseNotification(self, id: DBusUInt32) -> None: ...

    @dbus_signal()
    def ActionInvoked(
        self, id: DBusUInt32, action_key: DBusStr
    ) -> Annotated[tuple[int, str], DBusSignature("us")]:
        return (id, action_key)

    @dbus_signal()
    def NotificationClosed(
        self, id: DBusUInt32, reason: DBusUInt32
    ) -> Annotated[tuple[int, int], DBusSignature("uu")]:
        return (id, reason)
