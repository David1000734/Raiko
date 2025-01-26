import discord
import logging
from discord.ext import commands

intents = discord.Intents.all()
intents.members = True

# Commands will be predicated with a '!',
# Enables all intents from developer portal
client = commands.Bot(command_prefix='!', intents=intents)

# Color. There is a better way to do this...
MAGENTA = "\033[35m"
GRAY = "\033[90m"
RESET = "\x1b[0m"
BLUE = "\033[34m"

# Logging
log = logging.basicConfig(
    format=f"{GRAY} %(asctime)s  {BLUE}%(levelname)s  {MAGENTA}%(name)s \t{RESET}%(message)s",  # noqa E501
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO
)
log = logging.getLogger(__name__)


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
