import inspect
import discord
from discord.ext import commands
import utils


class Miscellaneous(commands.Cog):

    def __init__(self, client, config, cogs):
        self.client = client
        self.Config = config
        self.cogs = cogs

        self.help_cache = {}

        self.client.remove_command("help")

        self.help.bruh = ""

    @commands.command(brief='{"admin": False}', aliases=["info"], help="Supplies information about the usage of each command in a certain category")
    async def help(self, ctx, command: str = None):

        # If the embed for the requested command is cached, retrieve and send it
        try:
            if self.help_cache[command] is not None:
                await ctx.send(embed=self.help_cache[command])
                return
        except KeyError:
            pass

        if command is not None:
            command = command.lower()

            if command.startswith("!"):
                command = command[1:]

        if command is None or command == "admin" or (command == "owner" and ctx.message.author.id in self.Config["owner_ids"]):

            embed = discord.Embed(
                title="",
                description="Use `" + self.Config["bot_prefix"] + inspect.getframeinfo(
                    inspect.currentframe()).function + " <command>` for information about a specific command",
                colour=discord.Colour(value=eval(self.Config["bot_colour"])),
            )

            embed.set_author(name=self.client.user.name + " commands", icon_url=self.client.user.avatar_url)

            # Iterate through each function within each cog
            for cog in self.cogs:
                out = ""
                for function in dir(cog[0]):

                    # Check if the function is a bot command by seeing if it has the help attribute
                    try:
                        help = eval("cog[0]." + function + ".help")
                    except AttributeError:
                        continue

                    # Skip the function if the type does not match the requested type
                    try:
                        data = eval(str(eval("cog[0]." + function + ".brief")))

                        if data["type"] != command:
                            continue

                    except (KeyError, TypeError):
                        if command is not None:
                            continue

                    # Add the function to the output string
                    if out == "":
                        out = "`" + self.Config["bot_prefix"] + function + "`"
                    else:
                        out = out + "  " + "`" + self.Config["bot_prefix"] + function + "`"

                if out != "":
                    embed.add_field(name="\u200b\n" + cog[1], value=out, inline=False)
        else:

            for cog in self.cogs:

                # Check if the function is a bot command by seeing if it has the help attribute
                try:
                    help = eval("cog[0]." + command + ".help")
                    break
                except AttributeError:
                    continue

            try:
                a = help
            except NameError:
                await ctx.send(utils.format_message(ctx, "There is no command named '" + command + "'. For a list of commands, use `" + self.Config["bot_prefix"] + "help`"))
                return

            # Skip the function if is restricted to owners and the user is not an owner
            try:
                data = eval(str(eval("cog[0]." + command + ".brief")))

                if data["type"] == "owner" and ctx.message.author.id not in self.Config["owner_ids"]:
                    await ctx.send(utils.format_message(ctx,
                                                        "There is no command named '" + command + "'. For a list of commands, use `" +
                                                        self.Config["bot_prefix"] + "help`"))
                    return
            except (KeyError, TypeError):
                await ctx.send(
                    utils.format_message(ctx, "Sorry, the help information for that command has not been added yet"))
                return

            syntax = ""
            try:
                if data["syntax"] is not None:
                    syntax = "\n\nSyntax: `" + self.Config["bot_prefix"] + data["syntax"] + "`"
            except KeyError:
                pass

            examples = ""
            try:
                if data["examples"] is not None:

                    for example in data["examples"]:
                        if examples == "":
                            examples = "\nExamples: ```" + self.Config["bot_prefix"] + example + "```"
                        else:
                            examples = examples + "  ```" + self.Config["bot_prefix"] + example + "```"
            except (NameError, KeyError):
                pass

            embed = discord.Embed(
                title="Command info:  " + self.Config["bot_prefix"] + command,
                description=help + syntax + examples,
                colour=discord.Colour(value=eval(self.Config["bot_colour"])),
            )

            embed.set_footer(text="Category: " + cog[1])

        self.help_cache[command] = embed
        await ctx.send(embed=embed)

