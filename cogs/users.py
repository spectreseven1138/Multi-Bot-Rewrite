import inspect
from discord.ext import commands
import os
import pytz
import commentjson as json
import utils


class Users(commands.Cog):

    def __init__(self, client, config):
        global cli

        self.client = client
        self.Config = config

    @commands.command(help="Sets the user's timezone to be used with timetable commands", brief='{"admin": False}')
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

    def __init__(self, id: int, config: dict, timetable: str = None, timezone: str = None, crypt_key_location: dict = None):
        if timezone is None:
            timezone = config["default_timezone"]
        self.id = id
        self.timetable = timetable
        self.timezone = timezone
        self.crypt_key_location = crypt_key_location

    # Save the user's data to its file
    def save(self):

        # Open / create user file for writing
        if is_user_saved(self.id):
            file = open("users/" + str(self.id) + ".json", "w")
        else:
            file = open("users/" + str(self.id) + ".json", "x")

        # Format user data as JSON and write it to the file
        data = json.dumps({"id": self.id, "timetable": self.timetable, "timezone": self.timezone, "crypt_key_location": self.crypt_key_location}, indent=4)
        file.write(data)
        file.close()


# Returns user object tied to the supplied ID
def get_user(id: int, config: dict):

    # Return error if user file does not exist
    if not is_user_saved(id):
        user = User(id, config)
        user.save()
        return user

    # Load JSON data from user file and return it as a User object
    file = open("users/" + str(id) + ".json", "r")
    data = json.loads(file.read())
    file.close()
    return User(data["id"], config, data["timetable"], data["timezone"], data["crypt_key_location"])


# Returns True if user with supplied ID has been created
def is_user_saved(id: int):
    for user in os.listdir("users"):
        if user == str(id) + ".json":
            return True
    return False

