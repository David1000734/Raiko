from raiko.types.reddit_type import Reddit
from raiko.types.music_type import Music
from typing import Optional


class Server(object):
    __guild_name = None
    __guild_id = 0

    def __init__(self, id: str, name: str):
        self.Reddit: Optional[Reddit] = None
        self.Music: Optional[Music] = None

        self.__guild_name = name
        self.__guild_id = id

        pass

    def get_reddit(self, id: int) -> Reddit:

        pass

    def get_music(self, id: int) -> Music:

        pass

    pass
