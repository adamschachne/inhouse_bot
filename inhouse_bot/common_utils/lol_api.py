import os
from riotwatcher import LolWatcher, ApiError

API_KEY = os.getenv("INHOUSE_BOT_RIOT_API_KEY")
# only NA for now
REGION = "na1"


class Lol_Api(object):
    _lol_watcher: LolWatcher

    def __init__(self):
        self._lol_watcher = None

    @property
    def api(self):
        if not self._lol_watcher:
            self._lol_watcher = LolWatcher(API_KEY)
        return self._lol_watcher

    @api.deleter
    def api(self):
        self._lol_watcher = None

    def get_summoner_by_name(self, summonerName: str):
        summoner = self.api.summoner.by_name(REGION, summonerName)
        return summoner
