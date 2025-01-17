from typing import Callable


class Command:
    def __init__(self, name: str, action: Callable, kwargs: dict):
        """
        :param action: The function (callback) that will be executed for the command.
        :param kwargs: The keyword arguments to pass to the action function.
        """
        self.name = name
        self.action = action
        self.kwargs = kwargs

    def run(self):
        """Execute the action with the given keyword arguments."""
        self.action(**self.kwargs)
