from os import environ

import dotenv

dotenv.load_dotenv()

REDIRECT_URI = environ.get("REDIRECT_URI")
DISCORD_CLIENT_ID = environ.get("CLIENT_ID")
DISCORD_CLIENT_SECRET = environ.get("CLIENT_SECRET")
