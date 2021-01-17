import datetime
import os

import discord

import cogs.users.main
from discord.ext import commands
import commentjson as json
import utils
from cryptography.fernet import Fernet


class Tasks(commands.Cog):

    def __init__(self, client, config: dict):
        self.client = client
        self.Config = config

        self.categories = {}

    async def load_categories(self):

        for guild in os.listdir(""):

            self.categories[int(guild)] = {}

            guild_obj = self.client.get_guild(int(guild))
            if guild_obj is None:
                guild_obj = self.client.get_user(int(guild))

            for category in os.listdir("tasks/" + guild):
                self.categories[int(guild)][category[:-5].lower()] = Tasks.Category(guild_obj, category[:-5])

            for cat in self.categories[int(guild)].values():
                await cat.load_tasks(self.Config, self.client)

    async def check_key_created(self, ctx, user):
        if user.crypt_key_location is None and utils.is_dmchannel(ctx):
            key = Fernet.generate_key()
            await ctx.send(utils.format_message(ctx,
                                                "Any tasks or categories you create from DMs are private and fully encrypted\nThis is your encryption key (it is only stored here):"))
            message = await ctx.send(str(key)[2:-1])
            await ctx.send(utils.format_message(ctx, "\u200b"))

            user.crypt_key_location = {"channel": message.channel.id, "message": message.id}
            user.save()

    class Category:

        def __init__(self, guild, name: str):
            self.guild = guild
            self.name = name
            self.file_path = "tasks/" + str(guild.id) + "/" + name + ".json"

            if not os.path.exists("tasks/" + str(guild.id)):
                os.mkdir("tasks/" + str(guild.id))

            # Create category file if it does not exist
            if not os.path.exists(self.file_path):
                f = open(self.file_path, "w")
                self.data_raw = {"tasks": {}, "name": self.name, "guild_id": self.guild.id}
                f.write(json.dumps(self.data_raw))
                f.close()
            # Load data from category file
            else:
                f = open(self.file_path, "r")
                self.data_raw = json.loads(f.read())
                f.close()

            self.tasks = {}

        async def load_tasks(self, config, client):

            if type(self.guild) is discord.user.User:

                user = cogs.users.main.get_user(self.guild.id, config)

                # Get the user's encryption key from the saved location
                key = await client.get_channel(user.crypt_key_location["channel"]).fetch_message(user.crypt_key_location["message"])
                key = key.content
                crypt = Fernet(str.encode(key))

                for task in self.data_raw["tasks"].values():
                    self.tasks[crypt.decrypt(str.encode(task["title"])).decode()] = Tasks.Task(crypt.decrypt(str.encode(task["title"])).decode(), crypt.decrypt(str.encode(task["description"])).decode(), crypt.decrypt(str.encode(task["due_date"])).decode())
            else:
                for task in self.data_raw["tasks"].values():
                    self.tasks[task["title"]] = Tasks.Task(task["title"], task["description"], task["due_date"])


        async def save(self, config, client):
            self.data_raw["tasks"] = {}

            if type(self.guild) is discord.user.User:

                user = cogs.users.main.get_user(self.guild.id, config)

                # Get the user's encryption key from the saved location
                key = await client.get_channel(user.crypt_key_location["channel"]).fetch_message(user.crypt_key_location["message"])
                key = key.content
                crypt = Fernet(str.encode(key))

                for task in self.tasks.values():
                    self.data_raw["tasks"][crypt.encrypt(str.encode(task.title)).decode()] = {"title": crypt.encrypt(str.encode(task.title)).decode(), "description": crypt.encrypt(str.encode(task.description)).decode(), "due_date": crypt.encrypt(str.encode(task.due_date)).decode()}
            else:
                for task in self.tasks.values():
                    self.data_raw["tasks"][task.title] = {"title": task.title, "description": task.description, "due_date": task.due_date}

            f = open(self.file_path, "w")
            f.write(json.dumps(self.data_raw))
            f.close()

            return self

    class Task:
        def __init__(self, title, description, due_date):
            self.title = title
            self.description = description
            self.due_date = due_date

    @commands.command()
    async def list(self, ctx):
        print(self.categories[ctx.message.author.id])
        for category in self.categories[ctx.message.author.id].keys():
            print(category)

    @commands.command()
    async def deletetask(self, ctx, *, data):

        parsed = utils.parse_quotes(data, quote_types=["()"])[0]

        category = parsed[0][1:-1]
        title = parsed[1][1:-1]

        await self.check_key_created(ctx, cogs.users.main.get_user(ctx.message.author.id, self.Config))


    @commands.command()
    async def tasks(self, ctx, *, category="main"):

        await self.check_key_created(ctx, cogs.users.main.get_user(ctx.message.author.id, self.Config))

        if utils.is_dmchannel(ctx):
            guild = ctx.message.author
        else:
            guild = ctx.message.guild

        await self.load_categories()

        # Create main category object for the current guild if it doesn't exist
        if guild.id not in self.categories.keys():
            self.categories[guild.id] = {"main": await Tasks.Category(guild, "Main").save(self.Config, self.client)}

        if category.lower() not in self.categories[guild.id].keys():
            if utils.is_dmchannel(ctx):
                await ctx.send(
                    utils.format_message(ctx, "The category '" + category + "' does not exist in your private tasks"))
            else:
                await ctx.send(
                    utils.format_message(ctx, "The category '" + category + "' does not exist in this server"))
            return

        if len(self.categories[guild.id][category.lower()].tasks.values()) == 0:
            await ctx.send(utils.format_message(ctx, "There are no tasks in the '" + category + "' category"))
            return

        tasks = ""
        embed = discord.Embed(
            title="Tasks in the '" + category + "' category:",
            description="\u200b",
            colour=discord.Colour(value=eval(self.Config["bot_colour"]))
        )

        for task in self.categories[guild.id][category.lower()].tasks.values():

            duedate_obj = datetime.datetime.strptime(task.due_date, '%Y-%m-%d')
            delta = (datetime.datetime.now() - duedate_obj).days

            if delta < 0:
                delta *= -1

            print(delta)

            embed.add_field(name=task.title + " - Due " + task.due_date + " (" + str(delta) + " days)", value=task.description)

            # tasks = tasks + "\n" + task.title + ": " + task.description + " (" + task.due_date + ")"

        await ctx.send(embed=embed)


    @commands.command()
    async def addcategory(self, ctx, *, category_name=None):
        if category_name is None:
            await utils.incorrect_syntax(ctx, "addcategory")
            return

        if utils.is_dmchannel(ctx):
            guild = ctx.message.author
        else:
            guild = ctx.message.guild

        await self.load_categories()

        # Create main category object for the current guild if it doesn't exist
        if guild.id not in self.categories.keys():
            self.categories[guild.id] = {"main": await Tasks.Category(guild, "Main").save(self.client, self.Config)}

        if category_name.lower() in self.categories[guild.id].keys():

            if utils.is_dmchannel(ctx):
                await ctx.send(utils.format_message(ctx, "A category with that name already exisis in your private tasks"))
            else:
                await ctx.send(utils.format_message(ctx, "A category with that name already exisis in this server"))

            return


        self.categories[guild.id][category_name.lower] = await Tasks.Category(guild, category_name).save(self.Config, self.client)
        await ctx.send(utils.format_message(ctx, "The category '" + category_name + "' has been created"))

        await self.load_categories()

    @commands.command(brief=str({"type": None, "syntax": "addtask (category) (title) (description) (due date (yy-mm-dd))", "examples": ["addtask (main) (Math HW) (Finish pages 16-21 of the online textbook) (2020-11-3)"]}), help="Adds a task to the specified category in the current server")
    async def addtask(self, ctx, *, input_text=None):

        parsed = utils.parse_quotes(input_text, ["()"])[0]

        # Check if enough data was entered by the user
        if len(parsed) != 4:
            await utils.incorrect_syntax(ctx, "addtask")
            return

        # Get parsed data
        category = parsed[0][1:-1]
        title = parsed[1][1:-1]
        description = parsed[2][1:-1]
        duedate = parsed[3][1:-1]

        # Parse duedate string to a datetime object
        if duedate.lower() == "none":
            duedate = None
        else:
            try:
                duedate_obj = datetime.datetime.strptime(duedate, '%Y-%m-%d')
            except ValueError:
                await ctx.send(utils.format_message(ctx,
                                                    "Please input a date in the format `(year-month-day)` or set it to `(none)`\nFor example: `(2020-11-7)` or `(none)`"))
                return

        if utils.is_dmchannel(ctx):
            guild_id = ctx.message.author.id
            user = cogs.users.main.get_user(guild_id, self.Config)

            await self.check_key_created(ctx, user)

            # Load saved categories
            await self.load_categories()

            # Create main category object for the current guild if it doesn't exist
            if guild_id not in self.categories.keys():
                self.categories[guild_id] = {"main": await Tasks.Category(ctx.message.author, "Main").save(self.Config, self.client)}
        else:
            guild_id = ctx.message.guild.id

            # Load saved categories
            await self.load_categories()

            # Create main category object for the current guild if it doesn't exist
            if guild_id not in self.categories.keys():
                self.categories[guild_id] = {"main": await Tasks.Category(ctx.message.guild, "Main").save(self.Config, self.client)}

        # End function if the specified category does not exist
        if category.lower() not in self.categories[guild_id].keys():

            categories = ""
            for cat in self.categories[guild_id].values():
                categories = cat.name + ", "
            if categories.endswith(", "):
                categories = categories[:-2]

            if utils.is_dmchannel(ctx):
                await ctx.send(utils.format_message(ctx,
                                                    "The category '" + category + "' does not exist in your private tasks\nExisting categories are: " + categories + "\n\nFor information on how to create a category, use `" +
                                                    self.Config["bot_prefix"] + "help addcategory`"))
            else:
                await ctx.send(utils.format_message(ctx,
                                                    "The category '" + category + "' does not exist in this server\nExisting categories in this server are: " + categories + "\n\nFor information on how to create a category, use `" +
                                                    self.Config["bot_prefix"] + "help addcategory`"))

            return

        # Create a new task object and add it to the specified category
        newtask = Tasks.Task(title, description, duedate)
        category = self.categories[guild_id][category.lower()]

        for task in category.tasks.keys():
            if task.lower() == title.lower():
                await ctx.send(utils.format_message(ctx, "A task with that title already exists in the '" + category.name + "' category"))
                return

        category.tasks[title] = newtask
        await category.save(self.Config, self.client)
        await ctx.send(utils.format_message(ctx, "The task '" + title + "' was added to the '" + category.name + "' category"))
        await self.load_categories()



