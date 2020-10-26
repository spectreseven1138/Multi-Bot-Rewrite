import asyncio
import inspect
import os
from http.client import InvalidURL

import urllib.request
import re
import urllib.parse as urlparse
import isodate
import requests
from youtube_dl.utils import DownloadError
from youtube_dl import YoutubeDL
from pyyoutube import Api as YtApi

import discord
from discord.ext import commands
from discord.utils import get
import utils

youtubedl_opts = {
    "quiet": False,
    "continue": True,
    'format': 'worstaudio/worst',
    "outtmpl": 'music_download/%(title)s.%(ext)s',
    # 'postprocessors': [{
    #     'key': 'FFmpegExtractAudio',
    #     'preferredcodec': 'mp3',
    #     'preferredquality': '192',
    # }]
}


class MusicCog(commands.Cog):

    def __init__(self, client, config: dict):
        self.client = client
        self.Config = config
        self.music_queue = {}
        self.paused = {}
        self.loop = {}
        self.skipped = {}
        self.restarted = {}
        self.voice_channels = {}
        self.YtApi = YtApi(api_key=self.Config["youtube_api_key"])

    @commands.command(pass_content=True)
    async def play(self, ctx, *, input: str = None):
        guild = ctx.message.guild

        # If the current guild has registered music channels, check if the current channel is one of those
        if str(guild.id) in self.Config["music_channels"]:
            if self.Config["music_channels"][str(guild.id)] != str(ctx.message.channel.id):
                await ctx.send(utils.format_message(ctx, "The `" + inspect.getframeinfo(
                    inspect.currentframe()).function + "` command can only be used in " + str(
                    self.client.get_channel(int(self.Config["music_channels"][str(guild.id)])).mention)))
                return

        # Attempt to connect the bot to the voice channel if it isn't already
        if get(self.client.voice_clients, guild=guild) is None:

            # Check if the user is in a voice channel
            if ctx.message.author.voice is None:
                await ctx.send(utils.format_message(ctx, "You must be in a voice channel to use this command"))
                return
            else:

                # Attempt to connect to the users's voice channel
                try:
                    await ctx.message.author.voice.channel.connect(timeout=1)
                    self.voice_channels[str(guild.id)] = ctx.message.author.voice.channel
                except Exception as e:
                    if str(e) == "'VoiceClient' object has no attribute 'ws'" or e.__class__ == TimeoutError:
                        await ctx.send(utils.format_message(ctx, self.Config["bot_name"] + " was unable to join the voice channel you are in\nPlease make sure that the channel's permssions are set correctly"))
                    else:
                        await ctx.send(utils.format_message(ctx, "An unknown error ocurred while trying to join the voice channel you are in:\n" + str(e)))
                    return

        # If there is no input, attempt to resume music playback
        elif input is None:
            voice = get(self.client.voice_clients, guild=guild)

            # If paused, resume
            if self.paused[ctx.message.guild.id]:
                voice.resume()
                self.paused[ctx.message.guild.id] = False
                await ctx.send(utils.format_message(ctx, "Music has been resumed"))
                return
            # Otherwise,
            else:
                await ctx.send(
                    utils.format_message(ctx,
                                        "You can play music by searching for a video or adding a YouTube URL: `" + self.Config[
                                            "bot_prefix"] + inspect.getframeinfo(
                                            inspect.currentframe()).function + " <search / URL>`"))
                return

        parsed = {}

        # Attempt to get video id from YouTube URL
        try:
            try:
                input = requests.get(input).url
            except:
                input = requests.get("http://" + input).url
        except:
            pass
        else:
            try:
                parsed = urlparse.parse_qs(urlparse.urlparse(input).query)
            except InvalidURL:
                pass

        # If an id was found, directly download the video
        if "v" in parsed.keys():
            download = "https://www.youtube.com/watch?v=" + parsed["v"][0]

        # Otherwise, download the first search result
        else:
            term = ""
            for char in input:
                if char == " ":
                    if term != "":
                        term = term + "+"
                else:
                    term = term + char

            html = urllib.request.urlopen("https://www.youtube.com/results?search_query=" + term)
            video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
            download = "https://www.youtube.com/watch?v=" + video_ids[0]

        # Get video title
        parsed = urlparse.parse_qs(urlparse.urlparse(download).query)
        video = self.YtApi.get_video_by_id(video_id=parsed["v"][0]).items[0]

        # Notify that audio is downloading
        await ctx.send(utils.format_message(ctx, "Loading  '" + video.snippet.title + "'  (" + str(
            isodate.parse_duration(video.contentDetails.duration)) + ")"))

        # Return function if video duration is greater than 1 hour
        if isodate.parse_duration(video.contentDetails.duration).seconds > 3600:
            await ctx.send(utils.format_message(ctx,
                                               "This video is more than 30 minutes long, so it might take a few seconds to load\nIf this is an extended video, 1 hour version, etc, please use `" +
                                               self.Config[
                                                   "bot_prefix"] + "loop` to loop the standard version instead"))

        # Download the audio, retry on DownloadError up to 5 times
        for i in range(0, 5):
            try:
                download_info = YoutubeDL(youtubedl_opts).extract_info(url=download)
                break
            except DownloadError:
                continue

        # Get the video's ID from the extracted info
        try:
            id = download_info["entries"][0]["id"]
        except KeyError:
            id = download_info["id"]

        # If the download failed on every retry, report the error to the affected users and all owners, then return
        except NameError as e:
            await ctx.send(
                utils.format_message(ctx, "An error occurred and the audio could not be downloaded\nError: " + str(e)))

            for owner in self.Config["owner_ids"]:
                self.client.get_user(int(owner)).send(
                    "An error occurred while downloading the audio for '" + video.snippet.title + "'  (" + str(
                        isodate.parse_duration(video.contentDetails.duration)) + ")\nGuild: " + guild.name)
            return

        # Rename the file to its VideoID
        for file in os.listdir("music_download"):
            if file.endswith(".webm") or file.endswith(".m4a") or file.endswith(".mkv") or file.endswith(".mp3"):
                os.rename("music_download/" + file, "music_download/" + id)

        # Create a music queue for the current guild if it does not exist
        if str(guild.id) not in self.music_queue.keys():
            self.music_queue[str(guild.id)] = []

        # Append video info to the current guild's music queue
        try:
            self.music_queue[str(guild.id)].append(
                [download_info["id"], download_info["title"], download_info["thumbnail"], download_info["uploader"]])
        except KeyError:
            entries = download_info["entries"][0]
            self.music_queue[str(guild.id)].append(
                [entries["id"], entries["title"], entries["thumbnail"], entries["uploader"]])

        # if guild.voice_client is None:
        #     try:
        #         await ctx.message.author.voice.channel.connect(timeout=1)
        #     except AttributeError:
        #         await ctx.send(utils.format_message(ctx, "You must be in a voice channel to use this command"))
        #         return

        await self.process_queue(ctx, False)

    # Skips the currently playing song, regardless of loop
    @commands.command(pass_content=True)
    async def skip(self, ctx):
        self.paused[ctx.message.guild.id] = False
        guild = ctx.message.guild
        voice = get(self.client.voice_clients, guild=guild)

        voice.stop()

        self.skipped[ctx.message.guild.id] = True

    # Restarts the currently playing song from the beginning
    @commands.command(pass_content=True)
    async def restart(self, ctx):
        self.paused[ctx.message.guild.id] = False
        guild = ctx.message.guild
        voice = get(self.client.voice_clients, guild=guild)

        voice.stop()

        self.restarted[ctx.message.guild.id] = True

    @commands.command(pass_context=True)
    async def loop(self, ctx):

        if ctx.message.guild.id not in self.loop.keys():
            self.loop[ctx.message.guild.id] = False

        if self.loop[ctx.message.guild.id]:
            self.loop[ctx.message.guild.id] = False
            await ctx.send(utils.format_message(ctx, "Loop has been disabled"))
        else:
            self.loop[ctx.message.guild.id] = True
            await ctx.send(utils.format_message(ctx, "Loop has been enabled"))

    @commands.command(pass_content=True)
    async def pause(self, ctx):
        guild = ctx.message.guild
        voice = get(self.client.voice_clients, guild=guild)

        try:
            if self.paused[ctx.message.guild.id]:
                await ctx.send(utils.format_message(ctx, "Music has already been paused"))

            elif voice.is_playing():
                self.paused[ctx.message.guild.id] = True
                voice.pause()
                await ctx.send(utils.format_message(ctx, "Music has been paused"))

            else:
                await ctx.send(utils.format_message(ctx, "Music is not playing at the moment"))
        except AttributeError:
            await ctx.send(utils.format_message(ctx, "Music is not playing at the moment"))

    async def process_queue(self, ctx, done):

        # Reconnect to the voice channel (because connection may time out automatically if download is slow)
        for voice_client in self.client.voice_clients:
            if voice_client.guild == ctx.message.guild:
                await voice_client.disconnect()
                break

        await self.client.get_channel(self.voice_channels[str(ctx.message.guild.id)].id).connect(timeout=1)

        # await self.voice_channels[str(ctx.message.guild.id)].connect(timeout=1)

        guild = ctx.message.guild
        voice = get(self.client.voice_clients, guild=guild)

        # Create paused and skipped variables for the current guild if they do not exist
        if ctx.message.guild.id not in self.paused.keys():
            self.paused[ctx.message.guild.id] = False
        if ctx.message.guild.id not in self.skipped.keys():
            self.skipped[ctx.message.guild.id] = False
        if ctx.message.guild.id not in self.restarted.keys():
            self.restarted[ctx.message.guild.id] = False

        if voice.is_playing() or self.paused[ctx.message.guild.id]:
            ind = len(self.music_queue[str(guild.id)]) - 1
            embed = discord.Embed(
                title=self.music_queue[str(guild.id)][ind][1],
                description=self.music_queue[str(guild.id)][ind][3],
                colour=discord.Colour(value=eval(self.Config["bot_colour"])),
                url="https://www.youtube.com/watch?v=" + self.music_queue[str(guild.id)][ind][0]
            )

            embed.set_image(url=self.music_queue[str(guild.id)][ind][2])

            embed.set_author(name="Added to queue:")

            await ctx.send(embed=embed)
            return

        if ctx.message.guild.id not in self.loop.keys():
            self.loop[ctx.message.guild.id] = False

        looping = False
        if ((done and not self.loop[guild.id]) or (done and self.skipped[guild.id])) and not self.restarted[guild.id]:
            self.skipped[guild.id] = False
            os.remove("music_download/" + self.music_queue[str(guild.id)].pop(0)[0])
        elif done:
            if self.restarted[guild.id]:
                self.restarted[guild.id] = False
                looping = "restart"
            else:
                looping = "loop"

        if len(self.music_queue[str(guild.id)]) == 0:
            await ctx.send("The end of the queue has been reached")
            await self.auto_leave_call(voice, ctx)
            return

        id = self.music_queue[str(guild.id)][0][0]

        voice.play(discord.FFmpegPCMAudio("music_download/" + id))

        embed = discord.Embed(
            title=self.music_queue[str(guild.id)][0][1],
            description=self.music_queue[str(guild.id)][0][3],
            colour=discord.Colour(value=eval(self.Config["bot_colour"])),
            url="https://www.youtube.com/watch?v=" + id
        )

        embed.set_image(url=self.music_queue[str(guild.id)][0][2])

        if looping == "loop":
            embed.set_author(name="Looping track:")
        elif looping == "restart":
            embed.set_author(name="Restarting track:")
        else:
            embed.set_author(name="Now playing:")

        if type(ctx) is int:
            channel = self.client.get_channel(int(self.Config["music_channels"][str(ctx)][0]))
            await channel.send(embed=embed)
        else:
            await ctx.send(embed=embed)

        while True:
            if not voice.is_playing() and not self.paused[ctx.message.guild.id]:
                await self.process_queue(ctx, True)
                return
            await asyncio.sleep(2)

    async def auto_leave_call(self, voice, ctx):
        await asyncio.sleep(self.Config["idle_music_connection_timeout"])
        if not voice.is_playing() and not self.paused[ctx.message.guild.id]:
            for voice_client in self.client.voice_clients:
                if voice_client.guild == ctx.message.guild:
                    await voice_client.disconnect()
                    await ctx.send(self.Config["bot_name"] + " left the music channel because nothing was playing")
                    return
