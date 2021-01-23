import datetime
import os

import discord
import lyricsgenius
from discord.ext import commands
from discord.ext.tasks import loop
from discord.utils import get
from pyyoutube import Api as YtApi
import commentjson as json
import utils
from youtubesearchpython import SearchVideos, SearchPlaylists
from youtube_dl import YoutubeDL, DownloadError

f = open("bot_config.json", "r")
YtApi = YtApi(api_key=json.loads(f.read())["youtube_api_key"])
f.close()


class Music(commands.Cog):

    def __init__(self, client, config: dict):

        self.client = client
        self.Config = config

        self.music_queue = {}
        self.voice_channels = {}

        self.finished_queue_check.start()

        self.genius = lyricsgenius.Genius(self.Config["genius_access_token"])

    @loop(seconds=1)
    async def finished_queue_check(self):
        for queue in self.music_queue.values():
            if len(queue.queue_list) > 0:
                if not queue.voice.is_playing() and not queue.paused and queue.queue_list[0].started:
                    await queue.play_next(slf=self)

    class Video:

        def __init__(self, videoid, download, voice):
            self.videoid = videoid
            self.download = download
            self.voice = voice
            self.started = False

            self.ytdl_opts = {
                "quiet": True,
                "continue": True,
                'format': 'worstaudio/worst',
                "outtmpl": 'cogs/music/downloads/' + self.videoid,
                'youtube_include_dash_manifest': False
            }

            if self.download:
                for i in range(10):
                    try:
                        self.details = YoutubeDL(self.ytdl_opts).extract_info(
                            url="https://www.youtube.com/watch?v=" + self.videoid, download=True)
                        break
                    except DownloadError:
                        pass

        def get_details(self):

            try:
                return self.details
            except AttributeError:

                for i in range(50):
                    try:
                        self.details = YoutubeDL(self.ytdl_opts).extract_info(
                            url="https://www.youtube.com/watch?v=" + self.videoid,
                            download=False)
                        break
                    except DownloadError:
                        continue
                return self.details

        def play(self):
            self.voice.stop()

            if self.videoid in os.listdir("cogs/music/downloads"):
                self.voice.play(discord.FFmpegPCMAudio(source="cogs/music/downloads/" + self.videoid))
            else:

                ffmpeg_opts = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                               'options': '-vn'}

                self.voice.play(discord.FFmpegPCMAudio(self.get_details()["formats"][0]["url"], **ffmpeg_opts))

            self.started = True

    # Playlist object built to contain and manage Video objects
    class Playlist:

        def __init__(self, playlistid, playlist_position, voice):
            self.playlistid = playlistid  # YouTube ID of playlist
            self.voice = voice  # Discord voice channel object
            self.playlist_position = playlist_position  # Current position (video) no. within playlist
            self.started = False  # If the playlist has started playing
            self.error = [None]  # Error information

            self.details = YoutubeDL().extract_info(url="https://www.youtube.com/playlist?list=" + self.playlistid,
                                                    download=False, process=False)  # Get general YouTube details about the playlist itself

            video_list = YtApi.get_playlist_items(playlist_id=self.playlistid, count=None).items  # Get the videos within the playlist

            # Set error if playlist position is out of range
            if playlist_position > len(video_list):
                self.error = ["POSITION OUT OF RANGE", len(video_list)]

            # Set self.videos to a list of Video objects using the video_list retrieved earlier
            else:
                self.videos = []
                for video in video_list:
                    self.videos.append(Music.Video(video.snippet.resourceId.videoId, False, self.voice))

        # Play the video at the current playlist position
        def play(self):
            self.videos[self.playlist_position - 1].play()
            self.started = True
            return self.videos[self.playlist_position - 1]

    # Queue object containing Playlists and Videos; created per server
    class Queue:

        def __init__(self, voice, ctx):
            self.queue_list = []  # List of Playlist and Video objects in order of queue position
            self.voice = voice  # Discord voice channel object
            self.ctx = ctx  # Discord context information

            self.started = False
            self.paused = False
            self.loop = False

        # Add a Video object to the queue using a YouTube video ID
        def add_video(self, videoid, download):
            video = Music.Video(videoid, download, self.voice)
            self.queue_list.append(video)
            return video

        # Add a Playlist object to the queue using a YouTube playlist ID
        def add_playlist(self, playlist_id, start_position):
            playlist = Music.Playlist(playlist_id, start_position, self.voice)

            if playlist.error[0] is None:
                self.queue_list.append(playlist)

            return playlist

        # Clear the queue and stop currently playing audio
        def clear(self):
            self.queue_list = []
            self.voice.stop()

        # Play the next item in queue
        async def play_next(self, slf, progress=None, embed_header="Now playing:", starting_new: bool = False, skip_playlist=False, skip_amount=1):

            # Whether or not to progress the queue (used for looping and restarting)
            if progress is None:

                if self.loop:
                    progress = False
                    embed_header = "Looping:"
                else:
                    progress = True

            # Set the skip amount to 1 if unspecified
            if skip_amount is None:
                skip_amount = 1

            # Progress the queue if necessary by removing the first video or progressing the playlist
            if progress:
                if type(self.queue_list[0]) == Music.Playlist:
                    if skip_playlist:
                        self.queue_list = self.queue_list[1:]
                        starting_new = True
                    else:
                        self.queue_list[0].playlist_position += skip_amount
                        if self.queue_list[0].playlist_position > len(self.queue_list[0].videos):
                            self.queue_list = self.queue_list[skip_amount:]
                            starting_new = True
                else:
                    starting_new = True
                    self.queue_list = self.queue_list[skip_amount:]

            # Send message and stop playing audio if the queue is now empty
            if len(self.queue_list) == 0:
                await self.ctx.send(utils.format_message(self.ctx, "The end of the queue has been reached"))
                self.voice.stop()

                # Delete existing downloaded files
                for file in os.listdir("cogs/music/downloads"):
                    os.remove("cogs/music/downloads/" + file)

                return

            self.paused = False
            self.queue_list[0].play()

            # Determine whether thumbnail should be small or not
            if "restarting" in embed_header.lower() or "looping" in embed_header.lower():
                small = True
            else:
                small = False

            # # If a new playlist started playing during this command, send a different embed header
            # if starting_new and type(self.queue_list[0]) == Music.Playlist:
            #     print(embed_header)
            #     await self.ctx.send(
            #         embed=Music.get_embed(slf, video_or_playlist=self.queue_list[0], small=small,
            #                               header_text="Starting playlist:"))
            # else:
            await self.ctx.send(
                embed=Music.get_embed(slf, video_or_playlist=self.queue_list[0], small=small,
                                      header_text=embed_header))

    # Generates a Discord embed message for updating playback status
    def get_embed(self, video_or_playlist, small: bool, header_text: str, playlist_add: bool = False):

        # Check if subject is a playlist
        if type(video_or_playlist) is Music.Playlist:
            playlist = video_or_playlist

            if playlist_add:
                url = "https://www.youtube.com/playlist?list=" + playlist.details["id"]
                footer = "Contains: " + str(len(playlist.videos)) + " videos   |   Creator: " + \
                         playlist.details["uploader"]
                image = None
            else:
                video_or_playlist = playlist.videos[playlist.playlist_position - 1]

                duration = str(datetime.timedelta(seconds=video_or_playlist.details["duration"]))
                if duration.startswith("0:"):
                    duration = duration[2:]

                url = "https://www.youtube.com/watch?v=" + video_or_playlist.details["id"] + "&list=" + \
                      playlist.details["id"]

                footer = "Playlist: " + playlist.details["title"] + "   |   Video " + str(
                    playlist.playlist_position) + " of " + str(len(playlist.videos)) + "   |   Uploader: " + \
                         video_or_playlist.get_details()["uploader"] + "   |   Duration: " + duration
                image = video_or_playlist.get_details()["thumbnail"]
        else:
            url = "https://www.youtube.com/watch?v=" + video_or_playlist.get_details()["id"]

            duration = str(datetime.timedelta(seconds=video_or_playlist.details["duration"]))
            if duration.startswith("0:"):
                duration = duration[2:]

            footer = "Duration: " + duration + "   |   Uploader: " + video_or_playlist.details["uploader"]
            image = video_or_playlist.get_details()["thumbnail"]

        embed = discord.Embed(
            title=video_or_playlist.details["title"],
            description="",
            colour=discord.Colour(value=eval(self.Config["bot_colour"])),
            url=url
        )

        if image is not None:
            if small:
                embed.set_thumbnail(url=image)
            else:
                embed.set_image(url=image)

        embed.set_author(name=header_text)
        embed.set_footer(text=footer)

        return embed

    # Returns true if the user of the command is in valid music voice and text channels
    async def check_user_in_valid_channel(self, ctx, check_music_playing: bool):

        guild_id = ctx.message.guild.id

        voice = ctx.message.author.voice

        if voice is None:
            await ctx.send(
                utils.format_message(ctx, "You must be in a voice channel in this server to use music commands"))
            return False
        elif voice.channel.guild != ctx.message.guild:
            await ctx.send(
                utils.format_message(ctx, "You must be in a voice channel in this server to use music commands"))
            return False

        if str(guild_id) in self.Config["music_text_channels"].keys():

            if ctx.message.channel.id in self.Config["music_text_channels"][str(guild_id)]:
                pass
            else:

                music_channels = self.Config["music_text_channels"][str(guild_id)]

                if len(self.Config["music_text_channels"][str(guild_id)]) == 1:
                    await ctx.send(utils.format_message(ctx,
                                                        "Music commands can only be used in " + self.client.get_channel(
                                                            music_channels[0]).mention))
                else:

                    channels_string = ""

                    for i, channel in enumerate(music_channels):

                        channel = self.client.get_channel(channel).mention

                        if channels_string == "":
                            channels_string = channel
                        elif i == len(music_channels) - 1:
                            channels_string = channels_string + ", and " + channel
                        else:
                            channels_string = channels_string + ", " + channel

                    await ctx.send(
                        utils.format_message(ctx, "Music commands can only be used in " + channels_string))

                return False
        else:
            if guild_id in self.music_queue.keys():
                if ctx.message.channel.id == self.music_queue[guild_id].ctx.message.channel.id:
                    pass
                else:
                    await ctx.send(utils.format_message(ctx, "Currently, music commands can only be used in " +
                                                        self.music_queue[guild_id].ctx.message.channel.mention))
                    return False
            else:
                return True

        if check_music_playing:
            if guild_id not in self.music_queue.keys():
                await ctx.send(utils.format_message(ctx, "Nothing is playing at the moment"))
                return False
            else:
                queue = self.music_queue[guild_id]

                if not queue.voice.is_playing() and not queue.paused:
                    await ctx.send(utils.format_message(ctx, "Nothing is playing at the moment"))
                    return False
                else:
                    return True

        return True

    # Clear the queue and stop current playback
    @commands.command(brief=str({"type": None, "syntax": "clear", "examples": ["clear"]}),
                      help="Clears the entire playback queue")
    async def clear(self, ctx):

        if not await self.check_user_in_valid_channel(ctx, True):
            return

        queue = self.music_queue[ctx.message.guild.id]
        queue.clear()
        await ctx.send(utils.format_message(ctx, "The queue has been cleared"))

    # Jump to an absolute position within the currently playing playlist
    @commands.command(brief=str({"type": None, "syntax": "jump <playlist (optional) <position to jump to>", "examples": ["jump 3", "jump playlist 12"]}), help="Jumps forward in the queue by the specified amount, or jumps to an absolute position in a playlist")
    async def jump(self, ctx, jump_position=None):

        if not await self.check_user_in_valid_channel(ctx, True):
            return

        # Check if jump_position is a valid int
        try:
            jump_position = int(jump_position)
        except (ValueError, TypeError):
            await utils.incorrect_syntax(ctx, "jump")
            return

        guild_id = ctx.message.guild.id
        queue = self.music_queue[guild_id]
        playlist = queue.queue_list[0]

        if type(playlist) is not Music.Playlist:
            await ctx.send(utils.format_message(ctx, "The currently playing track is not part of a playlist"))
            return

        if jump_position < 1:
            await ctx.send(utils.format_message(ctx, "Please specify a position to jump to between 1 and the total size of the playlist (" + str(len(playlist.videos)) + ")"))
        elif jump_position > len(playlist.videos):
            await ctx.send(utils.format_message(ctx, "The position " + str(jump_position) + " cannot be jumped to because there are only " + str(len(playlist.videos)) + " items in the current playlist"))
            return
        elif jump_position == playlist.playlist_position:
            await ctx.send(utils.format_message(ctx, "The item at position " + str(jump_position) + " of the playlist is already being played"))
            return

        playlist.playlist_position = jump_position
        await queue.play_next(slf=self, progress=False, embed_header="Jumped to:")

        # self.music_queue[guild_id].queue_list[0].playlist_position = jump_position
        # await self.music_queue[guild_id].play_next(slf=self, progress=False, embed_header="Jumped to:")

    @commands.command(brief=str({"type": None, "syntax": "pause", "examples": ["pause"]}),
                      help="Pauses the currenly playing track")
    async def pause(self, ctx):

        if not await self.check_user_in_valid_channel(ctx, True):
            return

        try:
            queue = self.music_queue[ctx.message.guild.id]
            if queue.paused:
                await ctx.send(utils.format_message(ctx, "Playback has already been paused"))
            elif queue.voice.is_playing():
                queue.paused = True
                queue.voice.pause()
                await ctx.send(utils.format_message(ctx, "Playback has been paused"))
            else:
                await ctx.send(utils.format_message(ctx, "Nothing is playing at the moment"))
        except (AttributeError, KeyError):
            await ctx.send(utils.format_message(ctx, "Nothing is playing in this server at the moment"))

    @commands.command(brief=str({"type": None, "syntax": "skip <playlist or amount (optional)>", "examples": ["skip", "skip playlist", "skip 3"]}),
                      help="Skips the specified amount of tracks (or 1 if unspecified), can also skip the current playlist if specified")
    async def skip(self, ctx, mode=None):

        if not await self.check_user_in_valid_channel(ctx, True):
            return

        queue = self.music_queue[ctx.message.guild.id]

        if type(mode) is str:
            mode = mode.lower()
            if mode != "playlist":

                try:
                    mode = int(mode)
                except ValueError:
                    await utils.incorrect_syntax(ctx, "skip")
                    return

        if mode == "playlist" and type(queue.queue_list[0]) is not Music.Playlist:
            await ctx.send(utils.format_message(ctx, "The currently playing track is not part of a playlist"))
            return

        await queue.play_next(progress=True, slf=self, skip_playlist=mode == "playlist", skip_amount=mode)



    @commands.command(brief=str({"type": None, "syntax": "restart", "examples": ["restart"]}),
                      help="Restarts the currently playing track from the beginning")
    async def restart(self, ctx):

        if not await self.check_user_in_valid_channel(ctx, True):
            return

        queue = self.music_queue[ctx.message.guild.id]
        await queue.play_next(progress=False, embed_header="Restarting:", slf=self)

    @commands.command(
        brief=str({"type": None, "syntax": "loop <on/off (optional)>", "examples": ["loop on", "loop off", "loop"]}),
        help="Sets loop to on or off, or toggles it. When loop is enabled, a track will restart when it ends")
    async def loop(self, ctx, onoff: str = None):

        if not await self.check_user_in_valid_channel(ctx, True):
            return

        queue = self.music_queue[ctx.message.guild.id]

        if onoff is not None:
            onoff = onoff.lower()

        if (onoff is None and queue.loop) or onoff == "off":

            if not queue.loop:
                await ctx.send(utils.format_message(ctx, "Loop is already disabled"))
                return

            queue.loop = False
            await ctx.send(utils.format_message(ctx, "Loop has been disabled"))
        elif (onoff is None and not queue.loop) or onoff == "on":

            if queue.loop:
                await ctx.send(utils.format_message(ctx, "Loop is already enabled"))
                return

            queue.loop = True
            await ctx.send(utils.format_message(ctx, "Loop has been enabled"))
        else:
            await utils.incorrect_syntax(ctx, "loop")

    @commands.command(brief=str({"type": None, "syntax": "download <search/URL>",
                                 "examples": ["download stickerbrush symphony",
                                              "download https://www.youtube.com/watch?v=dQw4w9WgXcQ"]}),
                      help="Same as the `play` command, but preloads the audio for smoother playback")
    async def download(self, ctx, *, search_or_url=None):
        await self.play(ctx=ctx, search_or_url=[search_or_url, "download"])

    @commands.command(brief=str({"type": None, "syntax": "playlist <[start position] (optional)> <search/URL>",
                                 "examples": ["playlist [42] persona 4 ost",
                                              "playlist https://www.youtube.com/playlist?list=PLBAF8C0CDA4778263"]}),
                      help="Adds a YouTube playlist from the specified URL or search to the queue")
    async def playlist(self, ctx, *, search_or_url=None):
        await self.play(ctx=ctx, search_or_url=[search_or_url, "playlist"])

    @commands.command(brief=str({"type": None, "syntax": "play <search/URL>", "examples": ["play mice on venus",
                                                                                           "play https://www.youtube.com/watch?v=dQw4w9WgXcQ"]}),
                      help="Searches for a YouTube video and plays it in the user's connected voice channel")
    async def play(self, ctx, *, search_or_url=None):

        guild = ctx.message.guild

        if type(search_or_url) is list:
            mode = search_or_url[1]
            search_or_url = search_or_url[0]
        else:
            mode = "play"

        if not await self.check_user_in_valid_channel(ctx, False):
            return

        if guild.id not in self.music_queue.keys():

            # If the bot isn't connected to a VC, attempt to connect
            if get(self.client.voice_clients, guild=guild) is None:

                # TODO: tw attribute error
                for i in range(5):
                    try:
                        await ctx.message.author.voice.channel.connect(timeout=1)
                        break
                    except DownloadError:
                        pass

            self.music_queue[guild.id] = Music.Queue(voice=get(self.client.voice_clients, guild=guild), ctx=ctx)

        queue = self.music_queue[guild.id]

        if search_or_url is None:
            if queue.paused and mode == "play":
                queue.voice.resume()
                queue.paused = False
                await ctx.send(utils.format_message(ctx, "Playback has been resumed"))
                return
            else:
                if mode == "download":
                    await utils.incorrect_syntax(ctx, "download")
                elif mode == "playlist":
                    await utils.incorrect_syntax(ctx, "playlist")
                else:
                    await utils.incorrect_syntax(ctx, "play")
                return
        else:

            if mode == "play" or mode == "download":

                parsed = utils.parse_url(search_or_url)

                if "v" in parsed.keys():
                    video_id = parsed["v"][0]
                else:
                    search_result = json.loads(SearchVideos(search_or_url, offset=1, mode="json", max_results=1).result())["search_result"]

                    if len(search_result) == 0:
                        await ctx.send(utils.format_message(ctx,
                                                            "No YouTube videos were found when searching for '" + search_or_url + "'"))
                        return

                    video_id = search_result[0]["id"]

                new_element = queue.add_video(video_id, mode == "download")

            elif mode == "playlist":

                parsed = utils.parse_quotes(search_or_url, quote_types=["[]"])

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

                parsed = utils.parse_url(search_url_string)

                if "list" in parsed.keys():
                    playlist_id = parsed["list"][0]
                else:
                    search_result = json.loads(SearchPlaylists(search_url_string, offset=1, mode="json", max_results=10).result())["search_result"]

                    if len(search_result) == 0:
                        await ctx.send(utils.format_message(ctx,
                                                            "No YouTube playlists were found when searching for '" + search_or_url + "'"))
                        return

                    playlist_id = search_result[0]["id"]

                new_element = queue.add_playlist(playlist_id, start_position=start_position)
                if new_element.error[0] == "POSITION OUT OF RANGE":
                    await ctx.send(utils.format_message(ctx, "The found playlist '" + new_element.details["title"] + "' only contains " + str(new_element.error[1]) + " videos, so the position you entered (" + str(start_position) + ") cannot be reached"))
                    return

        if len(queue.queue_list) == 1:
            queue.paused = False

            await queue.play_next(slf=self, progress=False, starting_new=True)
        else:
            embed = self.get_embed(video_or_playlist=new_element, small=True, header_text="Added to queue:",
                                   playlist_add=True)
            await ctx.send(embed=embed)

    @commands.command(brief=str({"type": None, "syntax": "lyrics <song name>", "examples": ["lyrics burn my dread", "lyrics"]}),
                      help="Displays the lyrics for a specified song from Genius.com, or displays lyrics of the currently playing song if nothing was specified")
    async def lyrics(self, ctx, *, song_name=None):

        if song_name is None:

            guild_id = ctx.message.guild.id
            queue = self.music_queue[guild_id]

            if guild_id not in self.music_queue.keys():
                await utils.incorrect_syntax(ctx, "lyrics")
                return
            elif not queue.voice.is_playing() and not queue.paused:
                await utils.incorrect_syntax(ctx, "lyrics")
                return

            song = queue.queue_list[0]
            if type(song) == self.Video:
                song_name = song.details["title"]
            else:
                song_name = song.videos[0].get_details["title"]

        song = self.genius.search_song(song_name)

        try:
            embed = discord.Embed(
                title=song.title,
                description=song.lyrics,
                colour=discord.Colour(value=eval(self.Config["bot_colour"])),
                url=song.url,
            )
        except AttributeError:
            await ctx.send(utils.format_message(ctx, "No lyrics exist for '" + song_name + "' on genius.com"))
            return

        embed.set_thumbnail(url=song.song_art_image_url)
        embed.set_footer(text="Album: " + str(song.album) + "   |   Artist: " + str(song.artist) + "   |   Date: " + str(song.year))
        await ctx.send(embed=embed)

    @commands.command(
        brief=str({"type": None, "syntax": "loop <on/off (optional)>", "examples": ["loop on", "loop off", "loop"]}),
        help="Sets loop to on or off, or toggles it. When loop is enabled, a track will restart when it ends")
    async def queue(self, ctx, position=None):

        queue = self.music_queue[ctx.message.guild.id].queue_list

        if len(queue) == 0:
            await ctx.send(utils.format_message(ctx, "Nothing is queued at the moment"))
            return

        if position is None:
            queue_list = ""
            for i, item in enumerate(queue):
                queue_list = queue_list + str(i + 1) + ": " + item.details["title"]

                if type(item) is self.Playlist:
                    queue_list = queue_list + " (playlist)"

                queue_list = queue_list + "\n"

            embed = discord.Embed(
                title="Current queue:",
                description=queue_list,
            )

            embed.set_footer(text="For details on a single queue item, use " + self.Config["bot_prefix"] + "queue [item number]")
        else:
            try:
                position = int(position)
            except TypeError:
                await utils.incorrect_syntax(ctx, "queue")
                return

            if position > len(queue):
                await ctx.send(utils.format_message(ctx, "There are only " + str(len(queue)) + " items queued"))
                return
            elif position < 1:
                await utils.incorrect_syntax(ctx, "queue")
                return

            item = queue[position - 1]

            print(item.details)

            if type(item) == self.Video:

                date = item.details["upload_date"][:-4] + " " + item.details["upload_date"][4:-2] + "." + item.details["upload_date"][6:]

                details = "Type: Video\nDuration: " + str(datetime.timedelta(seconds=item.details["duration"])) + "\nUploader: " + item.details["uploader"] + "\nUpload date: " + date
                url = "https://www.youtube.com/watch?v=" + item.details["id"]
            else:

                details = "Type: Playlist\nContains: " + str(len(item.videos)) + " videos\nCreated by: " + item.details["uploader"]
                url = "https://www.youtube.com/playlist?list=" + item.details["id"]

            embed = discord.Embed(
                title=item.details["title"],
                description=details,
                url=url
            )

            embed.set_footer(text="Item " + str(position) + " of " + str(len(queue)) + " in queue")

        await ctx.send(embed=embed)


    @commands.command(brief=str({"type": "owner", "syntax": "rickroll <guild id / all>",
                                 "examples": ["rickroll 592625382205947904", "rickroll all"]}),
                      help="Plays a song in the specified guild's music channel, or all guilds")
    async def rickroll(self, ctx, guild_id: str = None):

        if ctx.message.author.id not in self.Config["owner_ids"]:
            return

        if guild_id is None:
            await ctx.send(utils.format_message(ctx, "Please specify a guild id, or use ALL for all guilds"))
            return
        elif guild_id.lower() == "all":
            queues = self.music_queue.values()
        else:
            queues = self.music_queue[ctx.message.guild.id]

        for queue in queues:
            queue.clear()

            queue.add_video("dQw4w9WgXcQ", True)
            await queue.play_next(progress=False, slf=self)
