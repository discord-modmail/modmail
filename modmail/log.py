import logging


class ModmailLogger(logging.Logger):
    """
    Custom logging class implementation.
    """

    def trace(self, msg, *args, **kwargs):
        self.log(logging.TRACE, msg, *args, **kwargs)

    def notice(self, msg, *args, **kwargs):
        self.log(logging.NOTICE, msg, *args, **kwargs)
