from raiko import client, load_extensions, log
from raiko.types import parameters  # noqa F401


# Upon bot is ready, exectute this constructor event
@client.event
async def on_ready():
    # load all cogs from "cogs" folder
    await load_extensions()

    parameters.init(client)
    # Do stuff with global variable in parameters

    # parameters.handler.add_server()

    print("Hello I'm ready, enter a command!")
    print("------------------------------")
    pass
# Constructor, END

# Start of main()
if (__name__ == "__main__"):
    import os

    # Import discord token
    discord_token = os.getenv("DISCORD_TOKEN")

    if (discord_token is not None):
        # Run the bot. We will be using the discord logger as well.
        client.run(discord_token, log_handler=log)
    else:
        print("Unable to find Discord Token.")
# Main, END
