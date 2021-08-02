import unittest

"""
Test custom logger
"""


class Test_Logs(unittest.TestCase):
    """Import modmail"""

    def test_import(self):
        """
        Import modmail
        """
        from modmail import log

        self.assertTrue(True)

    def test_logging(self):
        """
        Log.
        """
        import logging

        from modmail.log import ModmailLogger

        log = logging.getLogger(__name__)
        self.assertIsInstance(log, ModmailLogger)
        log.notice("ALERT")
        log.trace("minor minor info")
