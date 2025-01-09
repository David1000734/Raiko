import os
import logging
from discord.ext import commands
from raiko.types import parameters      # noqa F401

discord_botspam = os.getenv("DISCORD_BOTSPAM")
log = logging.getLogger(__name__)
# log.setLevel(logging.DEBUG)


class Greetings (commands.Cog):
    def __init__(self, client):
        self.client = client

    # Hello event, ctx: "inputs" from discord
    @commands.command()
    async def hello(self, ctx):
        # Do stuff with global variable
        log.debug(f"Before: {parameters.Server_Handler.server_list}")
        # parameters.Server_Handler.server_list[55] = "Good morning sir"     # DEBUG # noqa E501
        log.debug(f"After: {parameters.Server_Handler.server_list}")

        await ctx.send("Hello from the bot!")

    @commands.command()
    async def hi(self, ctx):
        if (parameters.handler.remove_server(55)):
            log.debug(f"Success {parameters.Server_Handler.server_list}")
        else:
            log.debug(f'Failed: {parameters.Server_Handler.server_list}')

    # Event, someone joins the server
    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = self.client.get_channel(discord_botspam)
        await channel.send("Welcome %s! Hope you enjoy your stay" %
                           (member.name))

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        channel = self.client.get_channel(discord_botspam)
        await channel.send("Goodbye %s. You strange mammal" %
                           (member.name))


async def setup(client):
    await client.add_cog(Greetings(client))
