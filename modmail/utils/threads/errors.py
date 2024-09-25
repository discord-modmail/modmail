class ThreadException(Exception):  # noqa: N818
    """The base error for threads, all threads errors should inherit from this exception."""

    pass


class ThreadNotFoundError(ThreadException):
    """Raised when a thread is not found."""

    pass


class ThreadAlreadyExistsError(ThreadException):
    """Raised when a thread already exists."""

    pass
