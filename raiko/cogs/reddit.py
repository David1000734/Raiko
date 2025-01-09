import asyncio                              # Import time keeping/looping
import asyncpraw                            # Reddit api. Async version
import asyncprawcore as apc
import raiko.misc.customException as ex     # Custom exceptions
from discord import SyncWebhook             # Connect to webhooks
from discord.ext import commands
from raiko.types import parameters          # Global class


class Reddit(commands.Cog):
    def __init__(self, client):
        self.client = client
        # reddit_obj = parameters.handler.Get_Server().Get_Reddit()
        # self.reddit_post = reddit_obj.Get_Post()
        self.reddit_post = []        # Store current posts
        self.reddit_instance = None  # The reddit API
        self.reddit_Task = []        # Running total of tasks created

    # *************** Non-command/event Functions ***************
    async def init_Reddit(self):
        import os

        # Instance must be created within async function
        # to allow for async for to work.
        self.reddit_instance = asyncpraw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_SECRET"),
            username=os.getenv("REDDIT_USERNAME"),
            password=os.getenv("REDDIT_PASSWORD"),
            user_agent="test_bot"
        )

    async def background_Task(self, sub_Name, get_limit, sleep_time, hook_URL):
        """
        Reddit background task to be continuously ran. Each post it gets will
        be placed into a global array and will keep track if it gets
        over the limit

        :param sub_Name: Name of the subreddit to be added.
        :param get_limit: Specified limit to number of post to get.
        :param sleep_time: How long should the task wait in-between running.
        :param hook_URL: URL of the webhook this task will use to post

        :note: This task does NOT do ANY checks. All inputs are assumed valid.
        """
        await self.client.wait_until_ready()        # Don't run while sleeping
        # Only done once.
        is_dup = False          # Bool, check for duplicate
        flip = True             # Flip how we append onto the list
        webhook = SyncWebhook.from_url(hook_URL)        # Connect to webhook

        # Time loop here
        while not self.client.is_closed():
            subreddit = await self.reddit_instance.subreddit(sub_Name, fetch=True)  # noqa: E501
            retrieved_post = subreddit.hot(limit=get_limit)
            async for submission in retrieved_post:
                # For more efficiency, use merge sort and then compare only one
                for post in self.reddit_post:
                    # Iterate through entire running total of the list.
                    if (post.id == submission.id):
                        is_dup = True
                        break

                # If a duplicate is found, don't print it.
                if (not is_dup):
                    # Only add if it wasn't on the list already

                    # We must flip how we add it from the first run
                    # and the continuous ones.
                    if (flip):
                        # Add to end of list
                        self.reddit_post.append(submission)
                    else:
                        # Add to beginning of list
                        self.reddit_post.insert(0, submission)

                    # Not a duplicate, print it.
                    # Build discord message here.
                    webhook.send(submission.title + ' ' + submission.url
                                 + '\n' + "https://www.reddit.com"
                                 + submission.permalink)
                # if, END
                # Otherwise, it is a duplicate. Don't do anything
                is_dup = False                      # Reset variable
            # async for, END

            # Check to see if we went past the limit
            # If the total number of post is greater than the number of
            # task times the limit, we went over. Remove the last few
            # Ex. limit = 10, 2 task.
            # If our total post is 23, we went over by 3 because 10 * 2 = 20
            if (len(self.reddit_post) >= len(self.reddit_Task) * get_limit):
                post_Counter = 0
                # We went over, remove the diference. Last to First
                for post in self.reddit_post:
                    # If the counter went over limit,
                    # remove the very last posts
                    if (post.subreddit.display_name == sub_Name and post_Counter >= get_limit):     # noqa: E501
                        # Find the correct name and remove only the
                        # post that went over the limit. (Last or oldest)
                        self.reddit_post.remove(post)

                    # Limit not reached, increment here
                    elif (post.subreddit.display_name == sub_Name):
                        # Increment counter
                        post_Counter += 1

                    # The subreddit we found is not related to
                    # this one, don't increment.
                    else:
                        # Just keep swimming
                        pass
                    # if else, END
                # For, END
            # Check limit, END

            # Change it to flip, This value will never change back
            flip = False

            await asyncio.sleep(sleep_time)         # Run every 'X' seconds
        # while, END
    # background task, END

    async def reddit_Add(self, arg, URL):
        """
        Function will attempt to create a new background task with
        the specified subreddit. All subreddit and webhook tests
        are also done here. If any fail, an exception is raised.

        :param arg: The subreddit to add
        :param URL: What is the URL of the webhook

        :note: All checks for the background task is done here
        """
        # Used to find out if task has already been created.
        found = False

        # Error check below, any exceptions will be caught by the
        # calling function.
        # *************** Check for Duplicate Subs ***************
        # Iterate through the task list
        for idx, currSub in enumerate(self.reddit_Task):
            # Search for a task with the that subreddit name
            if (currSub.get_name() == arg):
                found = True
                break               # Exit loop
            # if task_name = name, END
        # For task list, END

        # If one is found, error
        if (found):
            raise apc.AsyncPrawcoreException(
                "Duplicate subreddit is not allowed."
            )
        # *************** Duplicate Subs, END ***************

        # *************** Check for Valid Subreddits ***************
        # Ensure that it has been instantiated.
        if (self.reddit_instance is None):
            await self.init_Reddit()

        # Find valid subreddits by attempting to get from them.
        # Get the subreddit
        subRed = await self.reddit_instance.subreddit(arg, fetch=True)

        # Attempt to search it
        async for submission in subRed.new(limit=3):
            pass
        # *************** Valid Subs, END ***************

        # *************** Check for Webhook URL ***************
        SyncWebhook.from_url(URL)       # Throws an exception if not found

        # *************** Webhook URL, END ***************
        # No exceptions were raised, thus, valid input

        # Create time loop. Continuously run this function.
        current_tasks = self.client.loop.create_task(self.background_Task(
                        sub_Name=arg, get_limit=5,
                        sleep_time=900, hook_URL=URL))

        # Set the name to be the same as the subreddit
        current_tasks.set_name(arg)
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
        for idx, currSub in enumerate(self.reddit_Task):
            # Search for a task with the that subreddit name
            if (currSub.get_name() == arg):
                # If one is found, remove it
                currSub.cancel()

                # Remove from the list
                self.reddit_Task.remove(currSub)

                await ctx.send(
                    "Successfully removed subreddit: \"%s\", from tasks." %
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

    # *************** Discord command/event Functions ***************
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
                        await self.reddit_Add(arg[1], arg[2])

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
            await ctx.send("Subreddit: \"%s\" Error: %s" % (arg[1], error))

        # Default catch all exceptions
        except Exception as error:
            await ctx.send("Unknown error has occured: %s" % error)

        # try except, END
    # Reddit command block, END
# Reddit class, END


async def setup(client):
    await client.add_cog(Reddit(client))
