from inhouse_bot.database_orm.session.session import bot_declarative_base, session_scope
from inhouse_bot.database_orm.tables.admin import Admin
from inhouse_bot.database_orm.tables.channel_information import ChannelInformation
from inhouse_bot.database_orm.tables.game import Game
from inhouse_bot.database_orm.tables.game_participant import GameParticipant
from inhouse_bot.database_orm.tables.player import Player
from inhouse_bot.database_orm.tables.player_rating import PlayerRating
from inhouse_bot.database_orm.tables.queue_player import QueuePlayer
from inhouse_bot.database_orm.tables.server_config import ServerConfig

bot_declarative_base.registry.configure()
