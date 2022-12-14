import os
from pyot.conf.model import activate_model, ModelConf
from pyot.conf.pipeline import activate_pipeline, PipelineConf

from inhouse_bot.common_utils.constants import RIOT_API_KEY


@activate_model("lol")
class LolModel(ModelConf):
    default_platform = "na1"
    default_region = "americas"
    default_version = "latest"
    default_locale = "en_us"


@activate_pipeline("lol")
class LolPipeline(PipelineConf):
    name = "lol_main"
    default = True
    stores = [
        {
            "backend": "pyot.stores.omnistone.Omnistone",
            "expirations": {
                "summoner_v4_by_name": 1000,
                "summoner_v4_by_puuid": 1000,
                "match_v4_match": 600,
                "match_v4_timeline": 600,
                "league_v4_summoner_entries": 600,
            },
        },
        {
            "backend": "pyot.stores.cdragon.CDragon",
        },
        {
            "backend": "pyot.stores.riotapi.RiotAPI",
            "api_key": RIOT_API_KEY,
        },
    ]
