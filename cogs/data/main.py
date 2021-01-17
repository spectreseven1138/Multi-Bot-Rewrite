import inspect
import locale
import re
from datetime import datetime
from urllib.parse import quote
from urllib.request import urlopen
import feedparser

import discord
import requests
from discord.ext import commands
import utils

from cogs.data import info

class Data(commands.Cog):

    def __init__(self, client, config):
        self.client = client
        self.Config = config

        self.oyister_cache = None

        self.covid_data_cache_time = None
        self.covid_data_cache = []

    @commands.command(pass_context=True)
    async def weather(self, ctx, *, city=None):

        if city is None:
            await utils.incorrect_syntax(ctx, "weather")
            return

        # Get search results for the inputted city
        search_result = requests.get("http://dataservice.accuweather.com/locations/v1/cities/search?apikey=" + self.Config["accuweather_api_key"] + "&q=" + quote(city))
        search_result = search_result.json()

        # Check if there were no search results, or if an error occurred
        if len(search_result) == 0:
            await ctx.send(utils.format_message(ctx, "There are no cities matching '" + city + "'"))
            return
        elif type(search_result) is dict:
            if search_result["Code"] == "ServiceUnavailable" and search_result["Message"] == "The allowed number of requests has been exceeded.":
                await ctx.send(utils.format_message(ctx, "Sorry, the maximum amount of daily weather requests (25) has been exceeded"))
            else:
                await ctx.send(utils.format_message(ctx, "An unknown error occurred while searching for that location\nCode: " + search_result["Code"] + "\nMessage: " + search_result["Message"]))
            return

        # Get the first result in the list
        search_result = search_result[0]

        # Get needed data from search result
        key = search_result["Key"]
        name = search_result["EnglishName"]
        country = search_result["Country"]["ID"]

        # Get weather data for the search result
        weather = requests.get("http://dataservice.accuweather.com/currentconditions/v1/" + key + "?apikey=" + self.Config["accuweather_api_key"] + "&details=true")
        weather = weather.json()[0]

        # Create a Discord embed containing the weather information
        embed = discord.Embed(
            title="Weather in " + name + ", " + country,
            description=weather["WeatherText"] + "\n\n",
            colour=discord.Colour(value=eval(self.Config["bot_colour"])),
            url=weather["Link"]
        )

        # Get the icon path equivalent to the icon index supplied by the API and create an attachment file with it
        icon = discord.File("weather_icons/" + info.weather_types[str(weather["WeatherIcon"])] + ".png", filename="icon.png")
        embed.set_thumbnail(url="attachment://icon.png")

        embed.add_field(name="Temperature", value=str(weather["Temperature"]["Metric"]["Value"]) + "°C", inline=True)
        embed.add_field(name="Feels like", value=str(weather["RealFeelTemperature"]["Metric"]["Value"]) + "°C", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Empty element to force the next element onto a new row

        embed.add_field(name="Humidity", value=str(weather["RelativeHumidity"]) + "%", inline=True)
        embed.add_field(name="Wind", value=str(weather["Wind"]["Speed"]["Metric"]["Value"]) + " " + str(weather["Wind"]["Speed"]["Metric"]["Unit"]), inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Empty element to force the next element onto a new row

        embed.set_footer(text="\u200b\nSource: AccuWeather")

        await ctx.send(embed=embed, file=icon)

    @commands.command(pass_context=True)
    async def covid(self, ctx, *, country=None):

        # If the user inputted "countries", output a list of valid countries
        if str(country).lower() == "countries":
            await ctx.send(utils.format_message(ctx, "List of countries:\n" + info.string_covid_countries_1))
            await ctx.send(info.string_covid_countries_2)
            return

        # If the user inputted a country, check if it's valid
        elif country is not None and re.sub('[^A-Za-z0-9]+', '', country).lower() not in info.covid_countries.keys():
            await ctx.send(utils.format_message(ctx,
                                                "That is not a valid country. To get a list of all countries, use `" +
                                                self.Config["bot_prefix"] + inspect.getframeinfo(
                                                    inspect.currentframe()).function + " countries`\n\nIf you don't specify a country, this command will show the worldwide statistics"))
            return

        # Check if data is cached
        if self.covid_data_cache:

            # If cached data is at least a day old, get new data from the API
            if int(self.covid_data_cache["Date"][5:7]) < datetime.now().month or int(self.covid_data_cache["Date"][8:10]) < datetime.now().day:
                data = eval(urlopen(url="https://api.covid19api.com/summary").read())
                self.covid_data_cache = data
                self.covid_data_cache_time = datetime.now()

            # If cached data is still new, use it
            else:
                data = self.covid_data_cache
        # If data is not cached, download data and cache it
        else:
            data = eval(urlopen(url="https://api.covid19api.com/summary").read())
            self.covid_data_cache = data
            self.covid_data_cache_time = datetime.now()

        # Get date from data
        date = data["Date"][:10]

        # If the user didn't input a country, use the global data
        if country is None:
            data = data["Global"]
            name = "Worldwide"
        else:
            data = data["Countries"][info.covid_countries[re.sub('[^A-Za-z0-9]+', '', country).lower()]]
            name = data["Country"]

        # Create a Discord embed with the data
        embed = discord.Embed(
            title=name + " COVID-19 statistics",
            description="As of " + date,
            colour=discord.Colour(value=eval(self.Config["bot_colour"])),
            url="https://www.google.com/search?q=covid+19+" + quote(name)
        )

        embed.add_field(name="\u200b\nNew cases:",
                        value=locale.format_string("%d", int(data["NewConfirmed"]), grouping=True), inline=True)
        embed.add_field(name="\u200b\nTotal cases:",
                        value=locale.format_string("%d", int(data["TotalConfirmed"]), grouping=True), inline=True)
        embed.add_field(name="\u200b", value="\u200b")

        embed.add_field(name="\u200b\nNew deaths:",
                        value=locale.format_string("%d", int(data["NewDeaths"]), grouping=True), inline=True)
        embed.add_field(name="\u200b\nTotal deaths:",
                        value=locale.format_string("%d", int(data["TotalDeaths"]), grouping=True), inline=True)
        embed.add_field(name="\u200b", value="\u200b")

        embed.add_field(name="\u200b\nNew recoveries:",
                        value=locale.format_string("%d", int(data["NewRecovered"]), grouping=True), inline=True)
        embed.add_field(name="\u200b\nTotal recoveries:",
                        value=locale.format_string("%d", int(data["TotalRecovered"]), grouping=True), inline=True)
        embed.add_field(name="\u200b", value="\u200b")

        embed.set_footer(text="\u200b\nSource:\nJohns Hopkins University (via covid19api.com)")

        await ctx.send(embed=embed)

    @commands.command(pass_context=True)
    async def oyister(self, ctx, *, input=None):

        if input is not None:
            data = str(input).lower()

        # Get OYISTER data if it isn't cached or a refresh was requested
        if input == "reload" or self.oyister_cache is None:
            NewsFeed = feedparser.parse("https://oyister.oyis.org/feed/")
            entries = NewsFeed.entries

            self.oyister_cache = {entry["title"]: entry for entry in entries}


        # Create a Discord embed containing the weather information
        embed = discord.Embed(
            title="THE OYISTER",
            description="The OYIS Digital Newspaper\n\u200b",
            colour=discord.Colour(value=eval(self.Config["bot_colour"])),
            url="https://oyister.oyis.org/"
        )

        embed.set_thumbnail(url="https://oyister.oyis.org/favicon.ico")

        for article in self.oyister_cache.values():
            print(article)
            embed.add_field(name=article["published"][5:-15] + " (" + article["author"] + ")", value="\u200b          [" + article["title"] + "](" + article["links"][0]["href"] + ")", inline=False)

        # embed.set_footer(text="\u200b\nSource: AccuWeather")

        await ctx.send(embed=embed)
