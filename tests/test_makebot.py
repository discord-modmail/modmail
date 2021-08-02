import unittest

"""
Test modmail basics

- import module
- create a bot object
"""


class Test_Bot_Base(unittest.TestCase):
    """Import modmail"""

    def test_import(self):
        """
        Import modmail
        """
        import modmail

        self.assertTrue(True)

    def test_bot_creation(self):
        """
        Create bot object
        """
        from modmail.bot import ModmailBot

        bot = ModmailBot()
        self.assertIsInstance(bot, ModmailBot)
