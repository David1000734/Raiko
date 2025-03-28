import asyncio                              # Import time keeping/looping
import asyncpraw                            # Reddit api. Async version
import asyncprawcore as apc
import logging
import raiko.misc.customException as ex     # Custom exceptions
import discord
from discord import SyncWebhook             # Connect to webhooks
from discord.ui import Button, View
from discord.ext import commands
from raiko.types import parameters, token_importer    # Global class

log = logging.getLogger(__name__)
# Set level for this file only
# log.setLevel(logging.DEBUG)


class Flair_View(View):
    def __init__(self, ctx, flair_list):
        '''
        Builds all the components needed for the flair buttons.
        Uses a custom button class (Check_UnCheck_Button)
        '''
        super().__init__()
        self.ctx = ctx
        self.value = None

        done_button = [x for x in self.children if x.custom_id == "Done"][0]

        for (flair) in flair_list:
            self.add_item(Check_UnCheck_Button(flair, self, done_button))

    @discord.ui.button(
        disabled=True,
        label="DONE",
        style=discord.ButtonStyle.primary,
        custom_id="Done"
    )
    async def done_button_callback(self, interaction, button):
        '''
        Will retrieve only those buttons that have been clicked,
        that is, those with the success button style.
        '''
        disallowed_flairs = []
        allowed_flairs = []

        # Iterate through all the buttons and find only those
        # with the sucess style (IE. has been clicked)
        for (x) in self.children:
            # Select all that is clicked
            if (x.style == discord.ButtonStyle.success):
                allowed_flairs.append(x.label)

            # Select all that is not clicked
            if (x.style == discord.ButtonStyle.secondary):
                # Create Blacklist
                disallowed_flairs.append(x.label)

        if (allowed_flairs):
            # If something was clicked, build the flair list
            self.clear_items()
            await interaction.response.send_message(
                f'Allowed flairs: {", ".join(allowed_flairs)}',
                view=self
            )

            # Pass flair blacklist and end interaction
            self.value = disallowed_flairs
            self.stop()
        else:
            # If no flairs were clicked, re-prompt
            button.disabled = True
            await self.ctx.send("Please specify at least one flair.")
            await interaction.response.edit_message(view=self)

    @discord.ui.button(
        label="Allow All",
        style=discord.ButtonStyle.primary
    )
    async def allow_all_button_callback(self, interaction, button):
        '''
        Interacting with this button will allow all flairs to be posted.
        Clicking this will end the interaction.
        '''
        flair_list = []

        # Iterate through all the buttons and select all
        for (x) in self.children:
            # Don't include "DONE" and "Allow All"
            if (x.style != discord.ButtonStyle.primary):
                flair_list.append(x.label)

        self.clear_items()
        await interaction.response.send_message(
            f'Allowed flairs: {", ".join(flair_list)}',
            view=self
        )

        # Empty list indicating no blacklist
        self.value = []
        self.stop()

    async def on_timeout(self):
        return

    async def on_error(self, interaction, error, item):
        await interaction.response.send_message(str(error))

    async def interaction_check(self, interaction) -> bool:
        if (interaction.user != self.ctx.author):
            await interaction.response.send_message("Only the author can interaction with this", ephemeral=True)    # noqa E501
            return False
        return True


class Check_UnCheck_Button(Button):
    def __init__(self, label, view, done_button):
        '''
        Serves as the actual flair buttons the user will interact
        with to specify which flairs they like.

        :param label: What should the button say
        :param view: The view used to house this button. (Parent)
        :param done_button: The "confirm" button
        '''
        # Button will start off as disabled
        super().__init__(
            label=label,
            style=discord.ButtonStyle.secondary,
            emoji="❌"
        )
        # Specifies what the NEXT click should do. Not the current one
        self.to_be_enabled = True
        self.MyView = view
        self.done_button = done_button

    async def callback(self, interaction):
        if (self.to_be_enabled):
            # Our "next" click should enable. That means enable now
            self.style = discord.ButtonStyle.success
            self.emoji = "✔"
        else:
            # Our "next" click should disable. That means disable now
            self.style = discord.ButtonStyle.secondary
            self.emoji = "❌"
        # Regardless of action above, flip the boolean.
        self.to_be_enabled = not self.to_be_enabled

        # Enable the "Done" button
        self.done_button.disabled = False

        # Update the Button UI
        await interaction.response.edit_message(view=self.MyView)


class Reddit(commands.Cog):
    def __init__(self, client):
        self.client = client
        # reddit_obj = parameters.handler.Get_Server().Get_Reddit()
        # self.reddit_post = reddit_obj.Get_Post()
        self.reddit_post = []        # Store current posts
        self.reddit_instance = None  # The reddit API
        self.reddit_Task = []        # Running total of tasks created

    # region Non-command/event Functions
    async def init_Reddit(self):
        # Instance must be created within async function
        # to allow for async for to work.
        self.reddit_instance = asyncpraw.Reddit(
            client_id=token_importer("REDDIT_CLIENT_ID"),
            client_secret=token_importer("REDDIT_SECRET"),
            username=token_importer("REDDIT_USERNAME"),
            password=token_importer("REDDIT_PASSWORD"),
            user_agent="test_bot"
        )

    async def background_task(
            self, sub_name: str, hook_URL: str, disallowed_flairs: list,
            post_limit: str = 5, sleep_time: str = 900,
            initial: bool = False
    ) -> None:
        """
        Reddit background task to be continuously ran. Each post it gets will
        be placed into a global array and will keep track if it gets
        over the limit

        :param sub_name: Name of the subreddit to be added.
        :param hook_URL: URL of the webhook this task will use to post.
        :param disallowed_flairs: Flairs not allowed from subreddit.
        :param post_limit: Specified limit to number of post to get.
        :param sleep_time: How long should the task wait in-between running.
        :param initial: If the initial X post should be put on discord.

        :note: This task does NOT do ANY checks. All inputs are assumed valid.
        """
        await self.client.wait_until_ready()        # Don't run while sleeping
        # Only done once.

        # Get the subreddit
        subreddit = await self.reddit_instance.subreddit(sub_name, fetch=True)
        webhook = SyncWebhook.from_url(hook_URL)    # Connect to webhook
        queue = []                      # Submission Queue
        if (not initial):
            # Filling the queue would result in no initial posting
            queue = [item async for item in subreddit.hot(limit=post_limit)]

        # Time loop here
        while not self.client.is_closed():
            new_submissions = []
            # Gather the "new" posts
            async for (item) in subreddit.hot(limit=post_limit):
                new_submissions.append(item)

            # Get the different items between these two list
            difference_list = list(set(new_submissions).difference(queue))

            # Print whatever different items we found from above
            for (item) in (difference_list):
                if (item.link_flair_text not in disallowed_flairs):
                    # New post found, post it and update list
                    webhook.send(
                        item.title + ' ' + item.url +
                        "\nhttps://www.reddit.com" +
                        item.permalink
                    )
            # For, END
            # This is now our new queue
            queue = new_submissions

            await asyncio.sleep(sleep_time)         # Run every 'X' seconds
        # while, END
    # background task, END

    async def flair_finder(self, subreddit) -> list:
        '''
        Function attempts to retrieve the flair list from the server.
        If it is now allowed to, then an empty list is returned instead.

        :param subreddit: The subreddit to search through
        '''
        # Find list of flairs subreddit may have
        try:
            flair_list = [
                x['text'] async for x in subreddit.flair.link_templates
            ]
        except apc.Forbidden as ex:
            # If a subreddit does not allow viewing of their flairs,
            # just send an empty list.
            log.debug(
                f"\"{subreddit.display_name}\" {ex} ({type(ex).__name__})"
            )
            flair_list = []
        return flair_list

    async def reddit_Add(self, ctx, subreddit_name, URL):
        """
        Function will attempt to create a new background task with
        the specified subreddit. All subreddit and webhook tests
        are also done here. If any fail, an exception is raised.

        :param subreddit_name: The subreddit to add
        :param URL: What is the URL of the webhook

        :note: All checks for the background task is done here
        """
        # Error check below, any exceptions will be caught by the
        # calling function.
        # *************** Check for Duplicate Subs ***************
        # Iterate through the task list
        for idx, currSub in enumerate(self.reddit_Task):
            # Search for a task with the that subreddit name
            if (currSub.get_name() == subreddit_name):
                raise apc.AsyncPrawcoreException(
                    "Duplicate subreddit is not allowed."
                )
            # if task_name = name, END
        # For task list, END

        # *************** Duplicate Subs, END ***************

        # *************** Check for Valid Subreddits ***************
        # Ensure that it has been instantiated.
        if (self.reddit_instance is None):
            await self.init_Reddit()

        # Find valid subreddits by attempting to get from them.
        # Get the subreddit
        subreddit = await self.reddit_instance.subreddit(
            subreddit_name, fetch=True
        )

        # Attempt to search it
        async for submission in subreddit.new(limit=3):
            pass
        # *************** Valid Subs, END ***************

        # *************** Check for Webhook URL ***************
        SyncWebhook.from_url(URL)       # Throws an exception if not found

        # *************** Webhook URL, END ***************

        # *************** Existance of Flairs ***************
        subreddit_flair_list = await self.flair_finder(subreddit)
        view = None
        # https://www.youtube.com/watch?v=kNUuYEWGOxA
        # https://www.reddit.com/r/redditdev/comments/njj4y0/getting_list_of_available_flairs_for_a_subreddit/
        # https://www.reddit.com/r/redditdev/comments/njj4y0/getting_list_of_available_flairs_for_a_subreddit/

        # Determine if the subreddit has flairs
        if (subreddit_flair_list):
            # If it does have flairs, ask which ones should be allowed.
            view = Flair_View(ctx, subreddit_flair_list)
            await ctx.send(
                f"Flairs were found for \"{subreddit_name}\". " +
                "Please specify which flairs to allow.",
                view=view
            )
            timedout = await view.wait()
            view = view.value

            # End on timeout
            if (timedout):
                await ctx.send("Timed out, action aborted.")
                return

        # *************** Existance of Flairs, END ***************

        # No exceptions were raised, thus, valid input

        # Create time loop. Continuously run this function.
        current_tasks = self.client.loop.create_task(
            self.background_task(
                sub_name=subreddit_name, hook_URL=URL,
                disallowed_flairs=view
            )
        )

        # Set the name to be the same as the subreddit
        current_tasks.set_name(subreddit_name)
        self.reddit_Task.append(current_tasks)      # store to array
        # If valid sub, END
    # reddit_add, END

    async def reddit_Remove(self, ctx, arg):
        """
        Function will attempt to remove a specified subreddit
        from the current list of background tasks. If it does not
        exist, an error message is printed and no action is taken.

        :param ctx: Method of printing
        :param arg: What subreddit to remove from list
        """
        found = False

        # Iterate through the task list
        for (idx, currSub) in enumerate(self.reddit_Task):
            # Search for a task with the that subreddit name
            if (currSub.get_name() == arg):
                # If one is found, remove it
                currSub.cancel()

                # Remove from the list
                self.reddit_Task.remove(currSub)

                await ctx.send(
                    "Successfully removed subreddit: \"%s\" from tasks." %
                    (arg)
                )

                found = True        # Set flag
                break               # Exit loop

        if (not found):
            await ctx.send(
                "Subreddit: \"%s\" not found. Unable to remove." %
                (arg)
            )
        else:
            # Also remove it's post from the list
            for post in self.reddit_post:
                # Look for the post that matches this subreddit
                if (post.subreddit.display_name == arg):
                    # If found, remove it
                    self.reddit_post.remove(post)
        # if else, END
    # removeSub, END

    async def reddit_List(self, ctx):
        """
        Function will simply print the current list of background tasks

        :param ctx: Method of printing
        """
        listName = []

        for currSub in self.reddit_Task:
            listName.append(currSub.get_name())

        await ctx.send("Current subreddits: %s" % ", ".join(listName))
    # list, END

    async def reddit_Clear(self, ctx):
        """
        Function will simply clear all subreddits from the list

        :param ctx: Method of printing
        """
        for currSub in self.reddit_Task:
            await ctx.send(
                "Removed subreddit: \"%s\", from tasks." %
                (currSub.get_name())
            )
            currSub.cancel()

        # Clear background task list
        self.reddit_Task.clear()

        # Clear post list
        self.reddit_post.clear()
    # Clear all, END

    async def reddit_Help(self, ctx):
        """
        Function will print a help message for how to use
        the reddit command.

        :param ctx: Method of printing
        """
        # Send help message. Formating...
        await ctx.send(
            "```\n"
            + " Help ".center(50, '_') + "\n\n"
            + "usage: !reddit [commands] ...\n"
            + "\t[commands]: add <subreddit> <webhook_URL>, remove <subreddit>, clear, list, help.\n\n"          # noqa: E501
            + "\t[subreddit]: Whatever the name of the subreddit it may be. Remember, "                          # noqa: E501
            + "banned or subreddits containing spaces are not allowed.\n\n"
            + "\t[webhook_URL]: Please provide the URL of a webhook that is created and set it up "              # noqa: E501
            + "within the server. Refer to this link for help https://www.youtube.com/watch?v=fKksxz2Gdnc.\n\n"  # noqa: E501
            + "add: Add the specified subreddit into the queue and post using the provided webhook.\n"           # noqa: E501
            + "remove: Remove the specified subreddit from tasks if it exist.\n"                                 # noqa: E501
            + "clear: Clear all subreddit from tasks.\n"
            + "list: Show all current subreddits running.\n"
            + "```"
        )

    # region Discord command/event Functions
    @commands.command()
    async def reddit(self, ctx, *arg):
        """
        Function handles all reddit related calls. It will take in
        an unspecified number of arguments and attempt to match them
        to a command. If unsuccessful, a usage message is printed.

        :param ctx: Method of printing
        :param arg: Full list of the user's command. Unspecified length
        """
        try:
            # arg[0] will will contain the command
            match arg[0].lower():
                # add command will add a new background task for the subreddit
                case "add":
                    # 3 is the correct number of arguments for this command
                    if (len(arg) != 3):
                        # 3 arguments were not provided, error
                        raise ex.UnknownCommand()
                    else:
                        # arg[1] contains the word
                        await self.reddit_Add(ctx, arg[1], arg[2])

                # Attempt to remove a reddit background task if one exist
                case "remove":
                    if (len(arg) > 2):
                        raise ex.InvalidSubreddit()
                    else:
                        # arg[1] contains the word
                        await self.reddit_Remove(ctx, arg[1])

                # Clear all existing reddit background task
                case "clear":
                    if (len(arg) > 1):
                        raise ex.UnknownCommand()
                    else:
                        await self.reddit_Clear(ctx)

                case "list":
                    if (len(arg) > 1):
                        raise ex.UnknownCommand()
                    else:
                        await self.reddit_List(ctx)

                case "help":
                    if (len(arg) > 1):
                        raise ex.UnknownCommand()
                    else:
                        await self.reddit_Help(ctx)

                # Default state
                case _:
                    # Have the try catch do the message
                    raise IndexError("")
            # Match, END

        # Tuple out of range when ran with "!reddit"
        # Thus prompt usage error
        except IndexError:
            await ctx.send("Usage: !reddit [command]\n"
                           "`!reddit help` for more info!")

        # Custom exceptions, unknowns
        except ex.UnknownCommand:
            await ctx.send("Unknown command: \"%s\"" % " ".join(arg))

        # Custom exception, invalid subreddits
        except ex.InvalidSubreddit:
            await ctx.send("Error: Subreddit \"%s\" is not allowed." %
                           (" ".join(arg[1:])))

        # Handle exceptions that comes from inside reddit_add function.
        except apc.AsyncPrawcoreException as error:
            log.warning(
                "Subreddit: \"%s\" has encountered an issue: %s"
                % (arg[1], error)
            )
            await ctx.send(f"Encountered an issue with \"{arg[1]}\".")

        # Default catch all exceptions
        except Exception as error:
            log.error("Unknown error for Reddit has occured: %s" % error)
            await ctx.send("Unknown Error, please check logs.")
            raise

        # try except, END
    # Reddit command block, END
# Reddit class, END


async def setup(client):
    await client.add_cog(Reddit(client))
