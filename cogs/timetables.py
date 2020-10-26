import inspect

from discord.ext import commands
from datetime import date, datetime
import pytz
import commentjson as json
from cogs import users
import utils
import os
import warnings

timetable_cache = {}


class TimeTableCog(commands.Cog):

    def __init__(self, client, config):
        self.client = client
        self.Config = config

    @commands.command(pass_context=True)
    async def tt(self, ctx, mode: str = None, *, data: str = None):

        # Get user from file
        user = users.get_user(ctx.message.author.id)

        # Parse data to list
        parsed = utils.parse(data)

        if mode is str:
            mode = mode.lower()

        if mode == "set":

            # Get and sort list of timetables
            timetables = os.listdir("timetables")

            for file in timetables:
                if not file.endswith(".json"):
                    timetables.remove(file)

            timetables.sort()

            # Check if passed value is int
            try:
                n = int(parsed[0])
            except TypeError:
                await ctx.send(utils.format_message(ctx, "You must pass a number from 1 to " + str(len(timetables)) + " Ex. `" + self.Config[
                    "bot_prefix"] + inspect.getframeinfo(
                                            inspect.currentframe()).function + " set 1`"))
                return

            # Check if passed int is valid, set timetable if it passes check
            if len(timetables) >= n > 0:
                user.timetable = timetables[n - 1][:-5]
                user.save()
                await ctx.send(utils.format_message(ctx, "Your timetable has been set to '" + timetables[n - 1][:-5] + "'"))
            else:
                await ctx.send(utils.format_message(ctx, "You must pass a number from 1 to " + str(len(timetables)) + " Ex. `" + self.Config[
                    "bot_prefix"] + inspect.getframeinfo(
                                            inspect.currentframe()).function + " set 1`"))

        # Ask user to set their timetable if it has not been set yet
        elif user.timetable is None:

            # Get and sort list of timetables
            timetables = os.listdir("timetables")
            timetables.sort()

            # Display all available timetables
            out = ""
            for i, timetable in enumerate(timetables):
                if timetable.endswith(".json"):
                    out = out + str(i + 1) + ": " + timetable[:-5] + "\n"

            await ctx.send(utils.format_message(ctx, "Please set a timetable to use with this bot `" + self.Config[
                "bot_prefix"] + inspect.getframeinfo(
                                            inspect.currentframe()).function + " set <Timetable no.>`\n" + out))
            return
        elif mode is None:

            # Get current time from user's set timezone
            tz = pytz.timezone(user.timezone)
            current_time = datetime.now(tz)

            # Format the current time so that it can be compared with the timetable
            formatted_time = int(str(current_time.hour) + str(current_time.minute))

            # Load the user's timetable from file or cache
            if user.timetable in timetable_cache.keys():
                current_timetable = timetable_cache[user.timetable]
            else:
                file = open("timetables/" + user.timetable + ".json", "r")
                current_timetable = json.loads(file.read())
                file.close()
                timetable_cache[user.timetable] = current_timetable

            # Get the current timetable alternation
            current_alternation = get_current_alternation(user)
            current_timetable = current_timetable["timetables"][current_alternation]

            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            out = ""

            # Get the current day's timetable
            try:
                current_day = current_timetable[days[current_time.weekday()>tt]]
            except KeyError:
                out = "You don't have any events scheduled for today"
            else:

                # Get the event for the current time if it exists
                for i, event in enumerate(current_day):
                    time = event[0]

                    # Check if event is scheduled for current time
                    if time[0] <= formatted_time < time[1]:

                        # Format time to readable (900 -> 9:00)
                        time = format_time_to_readable(time)

                        # Set output for current event
                        out = out + "Your currently scheduled event is " + event[1] + " (" + time[0] + "~" + time[
                            1] + ")"

                        # Check if the next event is in the same timetable
                        if i + 1 != len(current_day):
                            # Get the next event and format its time to readable
                            event = current_day[i + 1]
                            time = format_time_to_readable(event[0])

                            # Set output for next event
                            out = out + "\nYour next scheduled event is " + event[
                                1] + " (" + time[0] + "~" + time[1] + ")"
                        break

            if out == "":
                out = "You don't have any events scheduled for now"

            if "next" not in out:

                first = True
                if current_alternation == len(timetable_cache[user.timetable]["timetables"]) - 1:
                    ia = 0
                else:
                    ia = current_alternation

                for x in range(0, len(timetable_cache[user.timetable]["timetables"])):

                    current_timetable = timetable_cache[user.timetable]["timetables"][ia]

                    if first:
                        i = current_time.weekday()
                        i += 1
                        if i == 7:
                            i = 0
                        first = False
                    else:
                        i = 0

                    print(ia)

                    while i != current_time.weekday():
                        print(i)
                        try:
                            if len(current_timetable[days[i]]) > 0:
                                # Get the next event and format its time to readable
                                event = current_timetable[days[i]][0]
                                time = format_time_to_readable(event[0])

                                # Set output for next event
                                out = out + "\nYour next scheduled event is " + event[
                                    1] + " (" + time[0] + "~" + time[1] + ") on " + days[i].title() + " (" + \
                                      current_timetable["name"] + ")"
                                break
                        except KeyError:
                            pass

                        i += 1
                        if i == 7:
                            break

                    if "next" in out:
                        break

                    ia += 1
                    if ia >= len(timetable_cache[user.timetable]["timetables"]):
                        ia = 0

                if "next" not in out:
                    out = "Your currently set timetable seems to be empty"

            out = user.timetable + " (" + timetable_cache[user.timetable]["timetables"][current_alternation]["name"] + ")\n" + out

            await ctx.send(utils.format_message(ctx, out))


def format_time_to_readable(time: list):
    if len(str(time[0])) == 3:
        time1 = "0" + str(time[0])[0] + ":" + str(time[0])[1] + str(time[0])[2]
    else:
        time1 = str(time[0])[0] + str(time[0])[1] + ":" + str(time[0])[2] + str(time[0])[3]

    if len(str(time[1])) == 3:
        time2 = "0" + str(time[1])[0] + ":" + str(time[1])[1] + str(time[1])[2]
    else:
        time2 = str(time[1])[0] + str(time[1])[1] + ":" + str(time[1])[2] + str(time[1])[3]

    return [time1, time2]


def get_current_alternation(user: users.User):
    timetable = timetable_cache[user.timetable]

    startdate = timetable["alternation start"]
    startdate = date(year=startdate[0], month=startdate[1], day=startdate[2])

    type = timetable["alternation type"]
    if type is None:
        return 0
    type = str(type).lower()

    tz = pytz.timezone(user.timezone)
    current_time = datetime.now(tz)
    today = date(year=current_time.year, month=current_time.month, day=current_time.day)

    if type == "weekly":
        delta = today - startdate
        tt = (delta.days // 7) % len(timetable["timetables"])
    elif type == "monthly":
        delta = (today.year - startdate.year) * 12 + today.month - startdate.month
        tt = delta % len(timetable["timetables"]) + 1
    elif type == "yearly":
        delta = today.year - startdate.year
        tt = delta % len(timetable["timetables"])
    else:
        warnings.warn("Invalid timetable alternation type")
        return 0

    return tt
