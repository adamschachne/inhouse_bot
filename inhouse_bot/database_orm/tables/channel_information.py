from sqlalchemy import Column, String, BigInteger
from sqlalchemy.orm import Mapped
from inhouse_bot.database_orm import bot_declarative_base


class ChannelInformation(bot_declarative_base):
    """Represents a channel used by the inhouse bot"""

    __tablename__ = "channel_information"

    # Discord ID
    id: Mapped[int] = Column(BigInteger, primary_key=True)

    # Useful for querying
    server_id: Mapped[int] = Column(BigInteger, nullable=False)

    # Current accepted values are "QUEUE" and "RANKING", but leaving it as a string for ease of updating
    channel_type: Mapped[str] = Column(String)

    def __repr__(self):
        return f"<ChannelInformation: {self.id=} | {self.server_id=}>"
