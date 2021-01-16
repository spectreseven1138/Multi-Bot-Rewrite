import os

import commentjson as json
import discord
from discord.ext import commands
from discord.ext.commands import bot

from cogs import timetables, users, tasks, data, miscellaneous, music_new

file = open("bot_config.json", "r")
Config = json.loads(file.read())
file.close()
client = commands.Bot(command_prefix=commands.when_mentioned_or(Config["bot_prefix"]), intents=discord.Intents.all())

cogs = [
    [users.Users, "Users"],
    [timetables.Timetables, "Timetables"],
    [tasks.Tasks, "Tasks"],
    [music_new.Music, "Music"],
    [data.Data, "Data"],
    [miscellaneous.Miscellaneous, "Miscellaneous"]
]

@client.event
async def on_ready():

    await set_status("playing", "Use " + Config["bot_prefix"] + "help for info")

    for id in Config["owner_ids"]:
        await client.get_user(id).send("Ready")

    # Disconnect from all voice channels
    for voice_client in client.voice_clients:
        await voice_client.disconnect()

    print("Ready")


@client.event
async def on_message(message):

    if message.author.bot:
        return

    # if message.content.startswith(Config["bot_prefix"]) and not users.is_user_saved(message.author.id):
    #     # newuser = users.User(message.author.id, Config)
    #     newuser.save()
    #
    #     await message.author.send(
    #         "Hello " + message.author.mention + ", it seems this is your first time using my commands\nFor information about what this bot can do, just use `" +
    #         Config["bot_prefix"] + "help`")

    await client.process_commands(message)


# Sets the bot's Discord status (playing, streaming, etc.)
async def set_status(type: str, activity: str, twitch_url: str = None):

    if type is None:
        return
    elif type == "playing":
        activity = discord.Game(name=activity)
    elif type == "streaming":
        if twitch_url is None:
            twitch_url = "https://www.twitch.tv/"
        activity = discord.Streaming(name=activity, url=twitch_url)
    elif type == "watching":
        activity = discord.Activity(type=discord.ActivityType.watching, name=activity)
    elif type == "listening":
        activity = discord.Activity(type=discord.ActivityType.listening, name=activity)
    else:
        raise Warning("Invalid bot status type")

    await client.change_presence(activity=activity)

if __name__ == '__main__':

    # Check if needed folders exist
    for folder in ("music_download", "tasks", "timetables", "users"):
        if not os.path.exists(folder):
            os.mkdir(folder)

    # Delete leftover music files
    for file in os.listdir("music_download"):
        os.remove("music_download/" + file)


    # # Start cogs
    for cog in cogs:

        if cog[0] == miscellaneous.Miscellaneous:
            client.add_cog(cog[0](client, Config, cogs))
        else:
            client.add_cog(cog[0](client, Config))

    # Run client
    client.run(Config["client_id"])
