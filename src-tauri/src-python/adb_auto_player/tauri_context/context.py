import contextvars

from pytauri import AppHandle

_profile_index: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "profile_index", default=None
)
_app_handle: contextvars.ContextVar[AppHandle | None] = contextvars.ContextVar(
    "active_app_handle", default=None
)


class TauriContext:
    @staticmethod
    def set_profile_index(profile_index: int | None):
        _profile_index.set(profile_index)

    @staticmethod
    def get_profile_index() -> int | None:
        return _profile_index.get()

    @staticmethod
    def set_app_handle(app_handle: AppHandle | None):
        _app_handle.set(app_handle)

    @staticmethod
    def get_app_handle() -> AppHandle | None:
        return _app_handle.get()
