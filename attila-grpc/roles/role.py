from enum import Enum


class Role(str, Enum):
    CLIENT = "client"
    AGENT = "agent"
    USER = "user"
    TOOL = "tool"
