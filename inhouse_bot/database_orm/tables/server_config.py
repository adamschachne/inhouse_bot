from sqlalchemy import Column, BigInteger, Integer, JSON
from sqlalchemy.orm import Mapped
from sqlalchemy.ext.mutable import MutableDict

from inhouse_bot.database_orm import bot_declarative_base


class ServerConfig(bot_declarative_base):
    """Table used for persistent server config"""

    __tablename__ = "server_config"

    # Auto-incremented ID field
    id: Mapped[int] = Column(Integer, primary_key=True)

    server_id: Mapped[int] = Column(BigInteger, unique=True)

    config: Mapped[dict[str, bool]] = Column(MutableDict.as_mutable(JSON))
