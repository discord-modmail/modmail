import dotenv
from os import environ
from typing import NamedTuple

dotenv.load_dotenv()

REDIRECT_URI = environ.get("REDIRECT_URI")


class Client(NamedTuple):
    client_id = environ.get("CLIENT_ID")
    client_secret = environ.get("CLIENT_SECRET")
