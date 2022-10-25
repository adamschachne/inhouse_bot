from sqlalchemy import Column, BigInteger
from sqlalchemy.orm import Mapped
from inhouse_bot.database_orm import bot_declarative_base


class Admin(bot_declarative_base):
    """Represents a Discord user with admin privileges"""

    __tablename__ = "admin"

    # Discord ID
    id: Mapped[int] = Column(BigInteger, primary_key=True)
    # Server ID
    server_id: Mapped[int] = Column(BigInteger, primary_key=True)

    def __repr__(self):
        return f"<Admin: {self.id=} | {self.server_id=}>"
