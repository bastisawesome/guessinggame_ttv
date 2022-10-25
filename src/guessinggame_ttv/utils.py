from dataclasses import dataclass


@dataclass
class Settings:
    channel: str
    token: str
    client_secret: str
    prefix: str = '!'
    logging_level: int = 2
