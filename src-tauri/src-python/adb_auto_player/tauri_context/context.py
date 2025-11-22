import contextvars
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytauri import AppHandle

_profile_index: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "profile_index", default=None
)
_app_handle: contextvars.ContextVar[AppHandle | None] = contextvars.ContextVar(
    "active_app_handle", default=None
)


class TauriContext:
    """Tauri context container."""

    @staticmethod
    def set_profile_index(profile_index: int | None):
        """Set App active Profile Index."""
        _profile_index.set(profile_index)

    @staticmethod
    def get_profile_index() -> int | None:
        """Get App active Profile Index."""
        return _profile_index.get()

    @staticmethod
    def set_app_handle(app_handle: AppHandle | None):
        """Set Tauri App Handle."""
        _app_handle.set(app_handle)

    @staticmethod
    def get_app_handle() -> AppHandle | None:
        """Returns Tauri App Handle."""
        return _app_handle.get()
