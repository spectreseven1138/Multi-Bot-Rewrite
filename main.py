import os

import commentjson as json
import discord
from discord.ext import commands
from discord.ext.tasks import loop
from cogs import timetables, users, tasks, music, weather

file = open("bot_config.json", "r")
Config = json.loads(file.read())
file.close()
client = commands.Bot(command_prefix=commands.when_mentioned_or(Config["bot_prefix"]), intents=discord.Intents.all())


@client.event
async def on_ready():

    await set_status(Config["bot_activity"])

    for id in Config["owner_ids"]:
        await client.get_user(id).send("ready")

    # Disconnect from all voice channels
    for voice_client in client.voice_clients:
        await voice_client.disconnect()

    print("Ready")

@client.event
async def on_message(message):

    if message.author.bot:
        return

    if message.content.startswith(Config["bot_prefix"]) and not users.is_user_saved(message.author.id):

        newuser = users.User(message.author.id, None, Config["default_timezone"])
        newuser.save()

        await message.author.send(
            "Hello " + message.author.mention + " it seems this is your first time using my commands\nFor information about what this bot can do, just use `" +
            Config["bot_prefix"] + "help`")

    await client.process_commands(message)


# Sets the bot's Discord status (playing, streaming, etc.)
async def set_status(data: list):

    type = data[0]

    if type is None:
        return
    elif type == "playing":
        activity = discord.Game(name=data[1])
    elif type == "streaming":
        if len(data) == 2:
            data.append("https://www.twitch.tv/")
        activity = discord.Streaming(name=data[1], url=data[2])
    elif type == "watching":
        activity = discord.Activity(type=discord.ActivityType.watching, name=data[1])
    elif type == "listening":
        activity = discord.Activity(type=discord.ActivityType.listening, name=data[1])
    else:
        raise Warning("Invalid bot status type")

    await client.change_presence(activity=activity)


# @loop(seconds=1)
# async def output_monitor():
#     import contextlib, io
#
#     f = io.StringIO()
#     contextlib.redirect_stdout(f)
#     output = f.getvalue()
#     print("MONITOROUTPUT: " + output)




if __name__ == '__main__':

    # Check if needed folders exist
    for folder in ("music_download", "tasks", "timetables", "users"):
        if not os.path.exists(folder):
            os.mkdir(folder)

    # Delete leftover music files (LEGACY)
    # for file in os.listdir("music_download"):
    #     os.remove("music_download/" + file)

    # Start cogs
    client.add_cog(users.UserCog(client, Config))
    client.add_cog(timetables.TimeTableCog(client, Config))
    client.add_cog(tasks.TasksCog(client, Config))
    client.add_cog(music.MusicCog(client, Config))
    client.add_cog(weather.WeatherCog(client, Config))

    # Start loops
    # output_monitor.start()

    # Run client
    client.run(Config["client_id"])