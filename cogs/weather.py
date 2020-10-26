import inspect
import locale
import re
from datetime import datetime
from urllib.parse import quote
from urllib.request import urlopen

import discord
import requests
from discord.ext import commands
import utils


class WeatherCog(commands.Cog):

    def __init__(self, client, config):
        self.client = client
        self.Config = config

        self.weather_types = {
            "1": "clear_day",
            "2": "clear_day",
            "3": "partly_cloudy_day",
            "4": "partly_cloudy_day",
            "5": "haze",
            "6": "cloudy",
            "7": "cloudy",
            "8": "cloudy",
            "9": None,
            "10": None,
            "11": "haze",
            "12": "rain",
            "13": "rain",
            "14": "rain",
            "15": "thunderstorm",
            "16": "thunderstorm",
            "17": "thunderstorm",
            "18": "rain",
            "19": "snow",
            "20": "snow",
            "21": "snow",
            "22": "snow",
            "23": "snow",
            "24": "snow",
            "25": "sleet",
            "26": "rain",
            "27": None,
            "28": None,
            "29": "snow",
            "30": "hot",
            "31": "cold",
            "32": "wind",
            "33": "clear_night",
            "34": "clear_night",
            "35": "partly_cloudy_night",
            "36": "partly_cloudy_night",
            "37": "haze",
            "38": "cloudy",
            "39": "rain",
            "40": "rain",
            "41": "thunderstorm",
            "42": "thunderstorm",
            "43": "snow",
            "44": "snow"

        }

        self.covid_data_cache_time = None
        self.covid_data_cache = []
        self.corona_countries = {'afghanistan': 0, 'albania': 1, 'algeria': 2, 'andorra': 3, 'angola': 4, 'antiguaandbarbuda': 5, 'argentina': 6, 'armenia': 7, 'australia': 8, 'austria': 9, 'azerbaijan': 10, 'bahamas': 11, 'bahrain': 12, 'bangladesh': 13, 'barbados': 14, 'belarus': 15, 'belgium': 16, 'belize': 17, 'benin': 18, 'bhutan': 19, 'bolivia': 20, 'bosniaandherzegovina': 21, 'botswana': 22, 'brazil': 23, 'bruneidarussalam': 24, 'bulgaria': 25, 'burkinafaso': 26, 'burundi': 27, 'cambodia': 28, 'cameroon': 29, 'canada': 30, 'capeverde': 31, 'centralafricanrepublic': 32, 'chad': 33, 'chile': 34, 'china': 35, 'colombia': 36, 'comoros': 37, 'congobrazzaville': 38, 'congokinshasa': 39, 'costarica': 40, 'croatia': 41, 'cuba': 42, 'cyprus': 43, 'czechrepublic': 44, 'ctedivoire': 45, 'denmark': 46, 'djibouti': 47, 'dominica': 48, 'dominicanrepublic': 49, 'ecuador': 50, 'egypt': 51, 'elsalvador': 52, 'equatorialguinea': 53, 'eritrea': 54, 'estonia': 55, 'ethiopia': 56, 'fiji': 57, 'finland': 58, 'france': 59, 'gabon': 60, 'gambia': 61, 'georgia': 62, 'germany': 63, 'ghana': 64, 'greece': 65, 'grenada': 66, 'guatemala': 67, 'guinea': 68, 'guineabissau': 69, 'guyana': 70, 'haiti': 71, 'holyseevaticancitystate': 72, 'honduras': 73, 'hungary': 74, 'iceland': 75, 'india': 76, 'indonesia': 77, 'iranislamicrepublicof': 78, 'iraq': 79, 'ireland': 80, 'israel': 81, 'italy': 82, 'jamaica': 83, 'japan': 84, 'jordan': 85, 'kazakhstan': 86, 'kenya': 87, 'koreasouth': 88, 'kuwait': 89, 'kyrgyzstan': 90, 'laopdr': 91, 'latvia': 92, 'lebanon': 93, 'lesotho': 94, 'liberia': 95, 'libya': 96, 'liechtenstein': 97, 'lithuania': 98, 'luxembourg': 99, 'macaosarchina': 100, 'macedoniarepublicof': 101, 'madagascar': 102, 'malawi': 103, 'malaysia': 104, 'maldives': 105, 'mali': 106, 'malta': 107, 'mauritania': 108, 'mauritius': 109, 'mexico': 110, 'moldova': 111, 'monaco': 112, 'mongolia': 113, 'montenegro': 114, 'morocco': 115, 'mozambique': 116, 'myanmar': 117, 'namibia': 118, 'nepal': 119, 'netherlands': 120, 'newzealand': 121, 'nicaragua': 122, 'niger': 123, 'nigeria': 124, 'norway': 125, 'oman': 126, 'pakistan': 127, 'palestinianterritory': 128, 'panama': 129, 'papuanewguinea': 130, 'paraguay': 131, 'peru': 132, 'philippines': 133, 'poland': 134, 'portugal': 135, 'qatar': 136, 'republicofkosovo': 137, 'romania': 138, 'russianfederation': 139, 'rwanda': 140, 'runion': 141, 'saintkittsandnevis': 142, 'saintlucia': 143, 'saintvincentandgrenadines': 144, 'sanmarino': 145, 'saotomeandprincipe': 146, 'saudiarabia': 147, 'senegal': 148, 'serbia': 149, 'seychelles': 150, 'sierraleone': 151, 'singapore': 152, 'slovakia': 153, 'slovenia': 154, 'solomonislands': 155, 'somalia': 156, 'southafrica': 157, 'southsudan': 158, 'spain': 159, 'srilanka': 160, 'sudan': 161, 'suriname': 162, 'swaziland': 163, 'sweden': 164, 'switzerland': 165, 'syrianarabrepublicsyria': 166, 'taiwanrepublicofchina': 167, 'tajikistan': 168, 'tanzaniaunitedrepublicof': 169, 'thailand': 170, 'timorleste': 171, 'togo': 172, 'trinidadandtobago': 173, 'tunisia': 174, 'turkey': 175, 'uganda': 176, 'ukraine': 177, 'unitedarabemirates': 178, 'unitedkingdom': 179, 'unitedstatesofamerica': 180, 'uruguay': 181, 'uzbekistan': 182, 'venezuelabolivarianrepublic': 183, 'vietnam': 184, 'westernsahara': 185, 'yemen': 186, 'zambia': 187, 'zimbabwe': 188}

        self.string_corona_countries_1 = "Afghanistan, Albania, Algeria, Andorra, Angola, Antigua and Barbuda, Argentina, Armenia, Australia, Austria, Azerbaijan, Bahamas, Bahrain, Bangladesh, Barbados, Belarus, Belgium, Belize, Benin, Bhutan, Bolivia, Bosnia and Herzegovina, Botswana, Brazil, Brunei Darussalam, Bulgaria, Burkina Faso, Burundi, Cambodia, Cameroon, Canada, Cape Verde, Central African Republic, Chad, Chile, China, Colombia, Comoros, Congo (Brazzaville), Congo (Kinshasa), Costa Rica, Croatia, Cuba, Cyprus, Czech Republic, Côte d'Ivoire, Denmark, Djibouti, Dominica, Dominican Republic, Ecuador, Egypt, El Salvador, Equatorial Guinea, Eritrea, Estonia, Ethiopia, Fiji, Finland, France, Gabon, Gambia, Georgia, Germany, Ghana, Greece, Grenada, Guatemala, Guinea, Guinea-Bissau, Guyana, Haiti, Holy See (Vatican City State), Honduras, Hungary, Iceland, India, Indonesia, Iran, Islamic Republic of, Iraq, Ireland, Israel, Italy, Jamaica, Japan, Jordan, Kazakhstan, Kenya, Korea (South), Kuwait, Kyrgyzstan, Lao PDR, Latvia, Lebanon, Lesotho, Liberia, Libya, Liechtenstein, Lithuania, Luxembourg, Macedonia, Republic of, Madagascar, Malawi, Malaysia, Maldives"
        self.string_corona_countries_2 = "Mali, Malta, Mauritania, Mauritius, Mexico, Moldova, Monaco, Mongolia, Montenegro, Morocco, Mozambique, Myanmar, Namibia, Nepal, Netherlands, New Zealand, Nicaragua, Niger, Nigeria, Norway, Oman, Pakistan, Palestinian Territory, Panama, Papua New Guinea, Paraguay, Peru, Philippines, Poland, Portugal, Qatar, Republic of Kosovo, Romania, Russian Federation, Rwanda, Saint Kitts and Nevis, Saint Lucia, Saint Vincent and Grenadines, San Marino, Sao Tome and Principe, Saudi Arabia, Senegal, Serbia, Seychelles, Sierra Leone, Singapore, Slovakia, Slovenia, Somalia, South Africa, South Sudan, Spain, Sri Lanka, Sudan, Suriname, Swaziland, Sweden, Switzerland, Syrian Arab Republic (Syria), Taiwan, Republic of China, Tajikistan, Tanzania, United Republic of, Thailand, Timor-Leste, Togo, Trinidad and Tobago, Tunisia, Turkey, Uganda, Ukraine, United Arab Emirates, United Kingdom, United States of America, Uruguay, Uzbekistan, Venezuela (Bolivarian Republic), Viet Nam, Western Sahara, Yemen, Zambia, Zimbabwe"

    @commands.command(pass_context=True)
    async def weather(self, ctx, *, city=None):

        if city is None:
            await ctx.send(utils.format_message(ctx, "Specify a city to lookup the weather of like this: `" + self.Config["bot_prefix"] + inspect.getframeinfo(
                                                    inspect.currentframe()).function + " <city>`"))
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
        icon = discord.File("weather_icons/" + self.weather_types[str(weather["WeatherIcon"])] + ".png", filename="icon.png")
        embed.set_thumbnail(url="attachment://icon.png")

        embed.add_field(name="Temperature", value=str(weather["Temperature"]["Metric"]["Value"]) + "°C", inline=True)
        embed.add_field(name="Feels like", value=str(weather["RealFeelTemperature"]["Metric"]["Value"]) + "°C", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Empty element to force the next element onto a new row

        embed.add_field(name="Humidity", value=str(weather["RelativeHumidity"]) + "%", inline=True)
        embed.add_field(name="Wind", value=str(weather["Wind"]["Speed"]["Metric"]["Value"]) + " " + str(weather["Wind"]["Speed"]["Metric"]["Unit"]), inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Empty element to force the next element onto a new row

        embed.set_footer(text="\u200b\nSource: AccuWeather")

        await ctx.send(embed=embed, file=icon)

    @commands.command(pass_content=True)
    async def covid(self, ctx, *, country=None):

        # If the user inputted "countries", output a list of valid countries
        if str(country).lower() == "countries":
            await ctx.send(utils.format_message(ctx, "List of countries:\n" + self.string_corona_countries_1))
            await ctx.send(self.string_corona_countries_2)
            return

        # If the user inputted a country, check if it's valid
        elif country is not None and re.sub('[^A-Za-z0-9]+', '', country).lower() not in self.corona_countries.keys():
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
            data = data["Countries"][self.corona_countries[re.sub('[^A-Za-z0-9]+', '', country).lower()]]
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
