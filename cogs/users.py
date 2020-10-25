import inspect
from discord.ext import commands
import os
import pytz
import commentjson as json
import utils


class UserCog(commands.Cog):

    def __init__(self, client, config):
        self.client = client
        self.Config = config

    @commands.command(pass_context=True)
    async def tz(self, ctx, mode: str, data: str):

        mode = mode.lower()
        user = get_user(ctx.message.author.id)

        if mode == "set":

            tz_is_valid = None
            for tz in pytz.all_timezones:
                if tz.lower() == data.lower():
                    tz_is_valid = tz
                    break

            if tz_is_valid is not None:
                await ctx.send(utils.format_message(ctx, "Your timezone has been set to " + tz_is_valid))
                user.timezone = tz_is_valid
                user.save()
            else:
                await ctx.send(utils.format_message(ctx, "'" + data + "' is not a valid timezone\nUse `" + self.Config[
                    "bot_prefix"] + inspect.getframeinfo(
                                            inspect.currentframe()).function + " search <search term>` to find your timezone or visit https://en.wikipedia.org/wiki/List_of_tz_database_time_zones for a full list of timezones"))
                
        if mode == "search":
            out = ""
            for tz in pytz.all_timezones:
                if data.lower() in tz.lower():
                    out = out + tz + "\n"
            await ctx.send(utils.format_message(ctx, utils.format_message(ctx, "Timezones containing '" + data + "':\n\n" + out)))


# Bot user object
class User:

    def __init__(self, id: int, timetable: str, timezone: str):
        self.id = id
        self.timetable = timetable
        self.timezone = timezone

    # Save the user's data to its file
    def save(self):

        # Open / create user file for writing
        if is_user_saved(self.id):
            file = open("users/" + str(self.id) + ".json", "w")
        else:
            file = open("users/" + str(self.id) + ".json", "x")

        # Format user data as JSON and write it to the file
        data = json.dumps({"id": self.id, "timetable": self.timetable, "timezone": self.timezone}, indent=4)
        file.write(data)
        file.close()


# Returns user object tied to the supplied ID
def get_user(id: int):

    # Return error if user file does not exist
    if not is_user_saved(id):
        return -1

    # Load JSON data from user file and return it as a User object
    file = open("users/" + str(id) + ".json", "r")
    data = json.loads(file.read())
    file.close()
    return User(data["id"], data["timetable"], data["timezone"])


# Returns True if user with supplied ID has been created
def is_user_saved(id: int):
    for user in os.listdir("users"):
        if user == str(id) + ".json":
            return True
    return False

