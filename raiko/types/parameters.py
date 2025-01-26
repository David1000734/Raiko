'''
Module used to hold a global variable that will be present
throughout the entire project.
'''
import logging
from discord.ext.commands import Bot
from raiko.types.server_type import Server

log = logging.getLogger(__name__)
# Use to show only this file's log info
# log.setLevel(logging.DEBUG)


# region Server Handler
def init(client: Bot):
    '''
    Initilization of global variables. ONLY the main should call this.
    '''
    # List of servers the bot is currently in and it's relavent data for each
    global handler
    handler = Server_Handler()

    # Also check to see if existing data already exist or not

    # Create a Server object for each server the bot is a part of
    for (guild) in (client.guilds):
        log.debug(f'Adding server: {guild.name} with id {guild.id} into list.')
        handler.add_server(guild.id, guild.name)
        pass

    log.debug(f'Built initial server list is: {handler.server_list}')


class Server_Handler(object):
    '''
    Class will hold the server list. This class will also contain
    methods for adding/removing servers to the list and any
    other methods that may be needed.
    '''

    server_list: dict = {}
    'Dictionary will be of type dict<int, Server>'

    def add_server(self, key: str, name: str) -> None:
        '''
        Add a server into the list.
        '''
        # Create server with it's id and name
        server = Server(key, name)

        # Create entry in list for that server and name
        self.server_list[key] = server

        pass

    def remove_server(self, key: str) -> bool:
        '''
        Remove a server from the list. Return success or fail
        '''
        server_removed = False

        # Check to see if a key exist
        if (key in self.server_list):
            # If it exist, remove it
            server_removed = True
            del self.server_list[key]

        return server_removed

    def get_server(self, key: str | int) -> Server:
        '''
        Provide the server if exist, None otherwise
        '''
        if (key) in self.server_list:
            return self.server_list[key]
        # If key does not exist in list, return None
        return None

    def __del__(self):
        # Deconstructor

        pass

# Server_Handler, END
