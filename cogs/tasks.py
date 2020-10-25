import os
from discord.channel import DMChannel
from discord.ext import commands
import commentjson as json
import utils
from cryptography.fernet import Fernet

category_template = {
    "tasks": {

    }
}


class TasksCog(commands.Cog):

    def __init__(self, client, config: dict):
        self.client = client
        self.Config = config

    @commands.command(pass_context=True)
    async def tasks(self, ctx, mode: str = None, *, data=None):
        mode = mode.lower()
        parsed = utils.parse(data)

        if mode == "add":
            if len(parsed) < 7:
                await ctx.send(utils.format_message(ctx, "You can add a task to the list of tasks like this: `" + self.Config[
                    "bot_prefix"] + "tasks add <category> & <title> & <description> & <due date (month/day)>`\n"
                                    "For example: `" + self.Config[
                                                  "bot_prefix"] + "tasks add Grade 10 & Math homework & Finish pages 6-9 & 10/23`"))

            else:

                split_keyword = "&"

                category = ""
                title = ""
                desc = ""
                date = ""

                current = ""
                for item in parsed:

                    if item == split_keyword:

                        # Check if current is empty or only whitespaces
                        if current == "":
                            current = " "
                        else:
                            for i, char in enumerate(current):
                                if char != " ":
                                    break
                                elif i + 1 == len(current):
                                    current = None
                                    break

                        if category == "":
                            category = current
                        elif title == "":
                            title = current
                        elif desc == "":
                            desc = current
                        elif date == "":
                            date = current
                            break
                        current = ""
                    else:
                        if current == "":
                            current = item
                        else:
                            current = current + " " + item

                if current != "":
                    if category == "":
                        category = current
                    elif title == "":
                        title = current
                    elif desc == "":
                        desc = current
                    elif date == "":
                        date = current

                # Set variables to None if they are set to the right keyword
                if desc == "%":
                    desc = None
                    print("descnone")
                if date == "%":
                    print("datenone")
                    date = None

                # Make sure all needed variables have been set
                if date == "":
                    await ctx.send(
                        utils.format_message(ctx, "You can add a task to the list of tasks like this: `" + self.Config[
                            "bot_prefix"] + "tasks add <category> / <title> / <description> / <due date (month/day)>`\n"
                                            "For example: `" + self.Config[
                                           "bot_prefix"] + "tasks add Math homework & Finish pages 6-9 & 10/23`"))
                    return

                if isinstance(ctx.channel, DMChannel):
                    top_folder = str(ctx.message.author.id)
                else:
                    top_folder = str(ctx.message.guild.id)

                # Check is categories folder exists for server/user
                exists = False
                for item in os.listdir("tasks"):

                    if os.path.isdir("tasks/" + item) and item == top_folder:
                        exists = True
                        break

                # Create server/user category folder and the 'all' category if the do not exist already
                if not exists:

                    if isinstance(ctx.channel, DMChannel):

                        key = Fernet.generate_key()

                        await ctx.send(utils.format_message(ctx, "All tasks set from DMs are private and only visible to you\nIn addition, they are encrypted with a random key so that your tasks are not readable to the bot owner\n\nThis is your unique encryption key (this is the only place it is stored):"))
                        key_message = await ctx.send(utils.format_message(ctx, str(key)[2:-1]))
                        await ctx.send(utils.format_message(ctx, "\u200b"))
                        await ctx.send(utils.format_message(ctx, "If you ever want to erase your key, use `" + self.Config["bot_prefix"] + "tasks deletekey`\nThis will permenantly erase your key and all of your tasks"))

                        os.mkdir("tasks/" + top_folder)
                        newfile = open("tasks/" + top_folder + "/all.json", "w")
                        newfile.write(json.dumps({"server_name": ctx.message.author.name, "is_dm": True, "key_location": key_message.id, "tasks": {}}))
                        newfile.close()

                    else:
                        os.mkdir("tasks/" + top_folder)
                        newfile = open("tasks/" + top_folder + "/all.json", "w")
                        newfile.write(json.dumps({"server_name": ctx.message.guild.name, "is_dm": False, "tasks": {}}))
                        newfile.close()

                # Check if category exists in server
                if category.lower() + ".json" not in os.listdir("tasks/" + top_folder):

                    out = "ALL"
                    for file in os.listdir("tasks/" + top_folder):
                        if file.endswith(".json") and file.lower() != "all.json":
                            out = out + ", " + file[:-5]

                    # TODO: You can create new task categories using `command`
                    if isinstance(ctx.server, DMChannel):
                        await ctx.send(utils.format_message(ctx,
                                                           "The category '" + category + "' does not exist\nAvailable categories for your private tasks are: " + out))
                    else:
                        await ctx.send(utils.format_message(ctx,
                                                           "The category '" + category + "' does not exist\nAvailable categories for this server are: " + out))
                    return

                # Check if task alerady exists within category
                file = open("tasks/" + top_folder + "/" + category.lower() + ".json", "r+")
                category_data = json.loads(file.read())
                file.seek(0)
                if title.lower() in category_data["tasks"].keys():

                    if category == "all":
                        category = "ALL"

                    await ctx.send(utils.format_message(ctx,
                                                  "A task with that title already exists in the '" + category + "' category of this server\n"
                                                                                                                "This task will be automatically removed 7 days after the due date, or you can delete it manually by using `" +
                                                  self.Config["bot_prefix"] + "tasks delete " + category + " & " + title + "`"))
                    file.close()
                    return

                if date is not None:
                    # Format due date to list
                    date_is_valid = True
                    try:
                        if len(date) == 3:
                            if date[1] == "/":
                                date = [int(date[0]), int(date[2])]
                        elif len(date) == 4:
                            if date[1] == "/":
                                date = [int(date[0]), int(date[2] + date[3])]
                            elif date[2] == "/":
                                date = [int(date[0] + date[1]), int(date[3])]
                        elif len(date) == 5:
                            if date[2] == "/":
                                date = [int(date[0] + date[1]), int(date[2] + date[3])]
                    except TypeError:
                        date_is_valid = False

                    # Check if due date is valid
                    if not date_is_valid or type(date) is str:
                        await ctx.send(utils.format_message(ctx,
                                                           "The entered due date is not valid\nPlease enter a date in the format `mm/dd` or use `%` if the task has no due date"))
                        return

                # Create the new task and add it to the category
                newtask = {"description": desc, "due_date": date, "creator": ctx.message.author.id}
                category_data["tasks"][title.lower()] = newtask
                file.write(json.dumps(category_data))
                file.close()
