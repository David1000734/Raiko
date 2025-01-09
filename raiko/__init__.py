import discord
import logging
from discord.ext import commands

intents = discord.Intents.all()
intents.members = True

# Commands will be predicated with a '!',
# Enables all intents from developer portal
client = commands.Bot(command_prefix='!', intents=intents)

# Logging
log = logging.basicConfig(
    format="%(asctime)s :: %(levelname)s :: %(name)s :: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO
)


async def load_extensions() -> None:
    import os

    # Find the path to this file.
    path_to_main = os.path.dirname(os.path.abspath(__file__))

    # Iterate through all files in cogs and add them
    for filename in os.listdir(path_to_main + '/cogs'):
        if ((filename != '__init__.py') and (filename.endswith("py"))):
            # File name without the .py at the end
            await client.load_extension("raiko.cogs." + filename[:-3])
        # If, END
    # For, END
# Load cogs, END
