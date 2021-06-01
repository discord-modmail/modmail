from os import environ

import dotenv

dotenv.load_dotenv()

REDIRECT_URI = environ.get("REDIRECT_URI")
CLIENT_ID = environ.get("CLIENT_ID")
CLIENT_SECRET = environ.get("CLIENT_SECRET")
