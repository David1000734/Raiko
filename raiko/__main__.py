from raiko import client, load_extensions, log
from raiko.types import parameters, token_importer


# Upon bot is ready, exectute this constructor event
@client.event
async def on_ready():
    # load all cogs from "cogs" folder
    await load_extensions()

    parameters.init(client)
    # Do stuff with global variable in parameters

    # parameters.handler.add_server()

    log.info("Hello I'm ready for a command!")
    log.info("------------------------------")
    pass
# Constructor, END


# Start of main()
if (__name__ == "__main__"):
    # Run the bot. We will be using the discord logger as well.
    client.run(token_importer("DISCORD_TOKEN"), log_handler=None)
