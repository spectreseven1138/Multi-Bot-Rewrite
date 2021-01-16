import asyncio
import inspect
import os

import urllib.request
import re
import urllib.parse as urlparse
import isodate
from discord import ClientException

from customlibs.youtube_dl.utils import DownloadError
from customlibs.youtube_dl import YoutubeDL
from pyyoutube import Api as YtApi

import discord
from discord.ext import commands
from discord.utils import get
import utils
import datetime


class Music(commands.Cog):

    def __init__(self, client, config: dict):

        self.download_progress = {}

        self.client = client
        self.Config = config
        self.music_queue = {}
        self.paused = {}
        self.loop = {}
        self.skipped = {}
        self.restarted = {}
        self.voice_channels = {}
        self.YtApi = YtApi(api_key=self.Config["youtube_api_key"])
        self.youtubedl_opts = {
            "quiet": True,
            "continue": True,
            'format': 'worstaudio/worst',
            "outtmpl": 'music_download/%(title)s.%(ext)s',
            # 'postprocessors': [{
            #     'key': 'FFmpegExtractAudio',
            #     'preferredcodec': 'mp3',
            #     'preferredquality': '192',
            # }]
        }


        self.ffmpeg_opts = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                            'options': '-vn'}

    @commands.command(brief=str({"type": None, "syntax": "play <search/URL>", "examples": ["play mice on venus", "play https://www.youtube.com/watch?v=dQw4w9WgXcQ"]}), help="Searches for a YouTube video and plays it in the user's connected voice channel")
    async def play(self, ctx, *, input: str = None):

        if input is None:
            await utils.incorrect_syntax(ctx, "play")
            return

        playlist = False
        download = False

        if type(ctx) is list:

            if ctx[0] == "download":
                download = True
            elif ctx[0] == "playlist":
                playlist = True
                search_url_string = ctx[2]["search_url_string"]
                start_position = ctx[2]["start_position"]

            ctx = ctx[1]

        guild = ctx.message.guild

        # If the current guild has registered music channels, check if the current channel is one of those
        if str(guild.id) in self.Config["music_channels"]:
            if self.Config["music_channels"][str(guild.id)] != ctx.message.channel.id:
                await ctx.send(utils.format_message(ctx, "The `" + inspect.getframeinfo(
                    inspect.currentframe()).function + "` command can only be used in " + str(
                    self.client.get_channel(int(self.Config["music_channels"][str(guild.id)])).mention)))
                return

        # Check if the user is connected to a voice channel
        if get(self.client.voice_clients, guild=guild) is None:

            print(ctx.message.author.voice.channel.guild.name)

            # Check if the user is in a voice channel
            if ctx.message.author.voice is None:
                await ctx.send(utils.format_message(ctx, "You must be in a voice channel to use this command"))
                return
            else:
                self.voice_channels[str(guild.id)] = ctx.message.author.voice.channel

        # If there is no input, attempt to resume music playback
        elif input is None:
            voice = get(self.client.voice_clients, guild=guild)

            # If paused, resume
            if self.paused[ctx.message.guild.id]:
                voice.resume()
                self.paused[ctx.message.guild.id] = False
                await ctx.send(utils.format_message(ctx, "Track has been resumed"))
                return
            # Otherwise,
            else:
                await ctx.send(
                    utils.format_message(ctx,
                                         "You can play music by searching for a video or adding a YouTube URL: `" +
                                         self.Config[
                                             "bot_prefix"] + inspect.getframeinfo(
                                             inspect.currentframe()).function + " <search / URL>`"))
                return

        # Attempt to parse input as a URL
        parsed = utils.parse_url(input)

        if playlist:
            # If a playlist id was not found in the URL, search YouTube for playlists instead
            if "list" in parsed.keys():
                playlist_items = self.YtApi.get_playlist_items(playlist_id=parsed["list"], count=None).items


            else:

                search_result = self.YtApi.search_by_keywords(q=search_url_string, search_type=["playlist"], count=1,
                                                              limit=1).items

                if len(search_result) == 0:
                    await ctx.send(utils.format_message(ctx,
                                                        "No playlists were found when searching for '" + search_url_string + "'"))
                    return

                download_url = "https://www.youtube.com/playlist?list=" + search_result[0].id.playlistId
        else:

            # If an id was found, directly download the video
            if "v" in parsed.keys():
                download_url = "https://www.youtube.com/watch?v=" + parsed["v"][0]

            # Otherwise, download the first search result
            else:

                search_result = self.YtApi.search_by_keywords(q=input, search_type=["video"], count=1, limit=1).items

                if len(search_result) == 0:
                    await ctx.send(utils.format_message(ctx, "No videos were found when searching for '" + input + "'"))
                    return

                download_url = "https://www.youtube.com/watch?v=" + search_result[0].id.videoId

                parsed = urlparse.parse_qs(urlparse.urlparse(download_url).query)

            # Notify that audio is downloading
            if download:

                # Get video title and duration
                video = self.YtApi.get_video_by_id(video_id=parsed["v"][0]).items[0]

                print(video.id)

                duration = str(isodate.parse_duration(video.contentDetails.duration))
                if duration.startswith("0:"):
                    duration = duration[2:]

                await ctx.send(utils.format_message(ctx, "Downloading  '" + video.snippet.title + "'  (" + duration + ")"))

        # Attempt to connect to the users's voice channel
        try:
            await self.voice_channels[str(guild.id)].connect(timeout=1)
        except Exception as e:
            if str(e) == "'VoiceClient' object has no attribute 'ws'" or e.__class__ == TimeoutError:
                await ctx.send(utils.format_message(ctx,
                                                    self.client.user.name + " was unable to join the voice channel you are in\nPlease make sure that the channel's permssions are set correctly"))
                return
            elif str(e) == "Already connected to a voice channel." and type(e) is ClientException:
                pass
            else:
                await ctx.send(utils.format_message(ctx,
                                                    "An unknown error ocurred while trying to join the voice channel you are in:\n" + str(
                                                        e)))
                return

        # Download the audio, retry on DownloadError up to 10 times
        for i in range(10):
            try:
                download_info = YoutubeDL(self.youtubedl_opts).extract_info(url=download_url, download=download, force_youtube=True)

                print(download_info)

                download_path = download_info["formats"][0]["url"]
                break
            except DownloadError:
                continue

        # Get the video's ID and duration from the extracted info
        try:
            duration = str(datetime.timedelta(seconds=download_info["duration"]))
            if duration.startswith("0:"):
                duration = duration[2:]
            id = download_info["id"]

        # If the download failed on every retry, report the error to the affected users and all owners, then return
        except UnboundLocalError as e:
            await ctx.send(
                utils.format_message(ctx, "An error occurred and the audio could not be downloaded, please try again or play a different video"))

            for owner in self.Config["owner_ids"]:
                await self.client.get_user(int(owner)).send(
                    "An error occurred while downloading the audio for '" + download_info["title"] + "'  (" + duration + ")\nGuild: " + guild.name + "\nError: " + str(e))
            return

        # If the video was downloaded, rename the file to its VideoID
        if download:
            for file in os.listdir("music_download"):
                if file.endswith(".webm") or file.endswith(".m4a") or file.endswith(".mkv") or file.endswith(".mp3"):
                    os.rename("music_download/" + file, "music_download/" + id)

            download_path = id

        # Create a music queue for the current guild if it does not exist
        if str(guild.id) not in self.music_queue.keys():
            self.music_queue[str(guild.id)] = []

        # Append video info to the current guild's music queue
        try:
            self.music_queue[str(guild.id)].append(
                [download_path, download_info["title"], download_info["thumbnail"], download_info["uploader"], duration,
                 download_url])
        except KeyError:
            print("BERUTEBRYUWTBR")
            entries = download_info["entries"][0]
            self.music_queue[str(guild.id)].append(
                [download_path, entries["title"], entries["thumbnail"], entries["uploader"], download_url])

        await self.process_queue(ctx, False)

    @commands.command(brief=str({"type": None, "syntax": "download <search/URL>", "examples": ["download stickerbrush symphony", "download https://www.youtube.com/watch?v=dQw4w9WgXcQ"]}), help="Same as the `play` command, but preloads the audio for smoother playback")
    async def download(self, ctx, *, input: str = None):

        if input is None:
            await utils.incorrect_syntax(ctx, "download")
            return

        await self.play(ctx=["download", ctx], input=input)


    @commands.command(brief=str({"type": None, "syntax": "playlist <[start position] (optional)> <search/URL>", "examples": ["playlist [42] persona 4 soundtrack", "playlist https://www.youtube.com/watch?list=PLBAF8C0CDA4778263"]}), help="Plays each video within a YouTube playlist in order, starting from the specified position")
    async def playlist(self, ctx, *, input: str = None):

        if input is None:
            await utils.incorrect_syntax(ctx, "playlist")
            return


        parsed = utils.parse_quotes(input, quote_types=["[]"])

        # Get the specified start position, if it exists
        start_position = parsed[0]

        if len(start_position) > 0:
            start_position = int(start_position[0][1:-1])
            if start_position == 0:
                start_position = 1

            parsed[1].pop(0)

        else:
            start_position = 1

        # Get the search/URL string
        search_url_string = None

        if len(parsed[1]) == 1:
            search_url_string = parsed[1][0]
        else:
            for element in parsed[1]:
                search_url_string = search_url_string + element

        # Remove whitespaces at start of the string
        temp = search_url_string
        search_url_string = ""
        for char in temp:
            if (search_url_string == "" and char != " ") or search_url_string != "":
                search_url_string = search_url_string + char

        await self.play(["playlist", ctx, {"search_url_string": search_url_string, "start_position": start_position}], input=input)


    @commands.command(brief=str({"type": None, "syntax": "skip", "examples": ["skip"]}), help="Skips the currently playing track and plays the next one in queue")
    async def skip(self, ctx):
        self.paused[ctx.message.guild.id] = False
        guild = ctx.message.guild
        voice = get(self.client.voice_clients, guild=guild)

        voice.stop()

        self.skipped[ctx.message.guild.id] = True

    @commands.command(brief=str({"type": None, "syntax": "clear", "examples": ["clear"]}), help="Clears the entire playback queue")
    async def clear(self, ctx):
        guild = ctx.message.guild

        self.paused[guild.id] = False

        voice = get(self.client.voice_clients, guild=guild)
        self.music_queue[str(guild.id)] = []
        voice.stop()



    @commands.command(brief=str({"type": None, "syntax": "restart", "examples": ["restart"]}), help="Restarts the currently playing track from the beginning")
    async def restart(self, ctx):
        self.paused[ctx.message.guild.id] = False
        guild = ctx.message.guild
        voice = get(self.client.voice_clients, guild=guild)

        voice.stop()

        self.restarted[ctx.message.guild.id] = True

    @commands.command(brief=str({"type": None, "syntax": "loop <on/off (optional)>", "examples": ["loop on", "loop off", "loop"]}), help="Sets loop to on or off, or toggles it. When loop is enabled, a track will restart when it ends")
    async def loop(self, ctx, onoff: str = None):

        guild_id = ctx.message.guild.id

        if guild_id not in self.loop.keys():
            self.loop[guild_id] = False

        if type(onoff) is str:
            onoff = onoff.lower()

        if (onoff is None and self.loop[guild_id]) or onoff == "off":

            if not self.loop[guild_id]:
                await ctx.send(utils.format_message(ctx, "Loop is already disabled"))
                return

            self.loop[guild_id] = False
            await ctx.send(utils.format_message(ctx, "Loop has been disabled"))
        elif (onoff is None and not self.loop[guild_id]) or onoff == "on":

            if self.loop[guild_id]:
                await ctx.send(utils.format_message(ctx, "Loop is already enabled"))
                return

            self.loop[guild_id] = True
            await ctx.send(utils.format_message(ctx, "Loop has been enabled"))
        else:
            await utils.incorrect_syntax(ctx, "loop")


    @commands.command(brief=str({"type": None, "syntax": "pause", "examples": ["pause"]}), help="Pauses the currenly playing track")
    async def pause(self, ctx):
        guild = ctx.message.guild
        voice = get(self.client.voice_clients, guild=guild)

        try:
            if self.paused[ctx.message.guild.id]:
                await ctx.send(utils.format_message(ctx, "Track has already been paused"))

            elif voice.is_playing():
                self.paused[ctx.message.guild.id] = True
                voice.pause()
                await ctx.send(utils.format_message(ctx, "Track has been paused"))

            else:
                await ctx.send(utils.format_message(ctx, "Nothing is playing at the moment"))
        except AttributeError:
            await ctx.send(utils.format_message(ctx, "Nothing is playing at the moment"))

    async def process_queue(self, ctx, done):

        guild = ctx.message.guild
        voice = get(self.client.voice_clients, guild=guild)

        # Create paused, skipped and restarted variables for the current guild if they do not exist
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
                description="",
                colour=discord.Colour(value=eval(self.Config["bot_colour"])),
                url=self.music_queue[str(guild.id)][ind][5]
            )

            # embed.set_image(url=self.music_queue[str(guild.id)][ind][2])

            embed.set_thumbnail(url=self.music_queue[str(guild.id)][ind][2])
            embed.set_author(name="Added to queue:")
            embed.set_footer(text="Duration: " + self.music_queue[str(guild.id)][ind][4] + "   |   Uploader: " + self.music_queue[str(guild.id)][ind][3])

            await ctx.send(embed=embed)
            return

        if ctx.message.guild.id not in self.loop.keys():
            self.loop[ctx.message.guild.id] = False

        looping = False
        if ((done and not self.loop[guild.id]) or (done and self.skipped[guild.id])) and not self.restarted[guild.id]:
            self.skipped[guild.id] = False

            if len(self.music_queue[str(guild.id)]) == 0:
                await ctx.send(utils.format_message(ctx, "The playback queue has been cleared"))

                # Delete downloaded music
                for file in os.listdir("music_download"):
                    os.remove("music_download/" + file)

                await self.auto_leave_call(voice, ctx)

                return
            else:
                self.music_queue[str(guild.id)].pop(0)

        elif done:
            if self.restarted[guild.id]:
                self.restarted[guild.id] = False
                looping = "restart"
            else:
                looping = "loop"

        # Check if queue is empty
        if len(self.music_queue[str(guild.id)]) == 0:
            await ctx.send("The end of the queue has been reached")

            # Delete downloaded music
            for file in os.listdir("music_download"):
                os.remove("music_download/" + file)

            await self.auto_leave_call(voice, ctx)
            return

        path = self.music_queue[str(guild.id)][0][0]

        if not path.startswith("https://"):
            voice.play(discord.FFmpegPCMAudio("music_download/" + path))
        else:
            voice.play(discord.FFmpegPCMAudio(path, **self.ffmpeg_opts))

        embed = discord.Embed(
            title=self.music_queue[str(guild.id)][0][1],
            description="",
            colour=discord.Colour(value=eval(self.Config["bot_colour"])),
            url=self.music_queue[str(guild.id)][0][5]
        )

        embed.set_image(url=self.music_queue[str(guild.id)][0][2])
        embed.set_footer(text="Duration: " + self.music_queue[str(guild.id)][0][4] + "   |   Uploader: " +
                              self.music_queue[str(guild.id)][0][3])
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
                    await ctx.send(self.client.user.name + " left the voice channel because nothing was playing")
                    return
