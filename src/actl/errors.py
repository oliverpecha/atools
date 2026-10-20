"""Public exception types for actl CLI mapping."""


class UsageError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class StateIntegrityError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EnvError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
