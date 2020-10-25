import inspect
import locale
import re
from urllib.request import urlopen

import discord
import requests
from discord.ext import commands
import utils

import ijson

class WeatherCog(commands.Cog):

    def __init__(self, client, config):
        self.client = client
        self.Config = config

        self.weather_types = {
            "01": "sunny",
            "02": "slightly cloudy",
            "03": "fairly cloudy",
            "04": "mostly cloudy",
            "09": "light rain",
            "10": "rain",
            "11": "thunderstorm",
            "13": "snow",
            "50": "mist"
        }

        self.citiesfile = open("openweather_data/cities.json", "rb")
        self.cities = ijson.basic_parse(self.citiesfile)

        self.countriesfile = open("openweather_data/countries.json", "rb")
        self.cities = ijson.basic_parse(self.countriesfile)

        self.corona_countries = {'afghanistan': 0, 'albania': 1, 'algeria': 2, 'andorra': 3, 'angola': 4,
                            'antiguaandbarbuda': 5, 'argentina': 6, 'armenia': 7, 'australia': 8, 'austria': 9,
                            'azerbaijan': 10, 'bahamas': 11, 'bahrain': 12, 'bangladesh': 13, 'barbados': 14,
                            'belarus': 15, 'belgium': 16, 'belize': 17, 'benin': 18, 'bhutan': 19, 'bolivia': 20,
                            'bosniaandherzegovina': 21, 'botswana': 22, 'brazil': 23, 'bruneidarussalam': 24,
                            'bulgaria': 25, 'burkinafaso': 26, 'burundi': 27, 'cambodia': 28, 'cameroon': 29,
                            'canada': 30, 'capeverde': 31, 'centralafricanrepublic': 32, 'chad': 33, 'chile': 34,
                            'china': 35, 'colombia': 36, 'comoros': 37, 'congobrazzaville': 38, 'congokinshasa': 39,
                            'costarica': 40, 'croatia': 41, 'cuba': 42, 'cyprus': 43, 'czechrepublic': 44,
                            'ctedivoire': 45, 'denmark': 46, 'djibouti': 47, 'dominica': 48, 'dominicanrepublic': 49,
                            'ecuador': 50, 'egypt': 51, 'elsalvador': 52, 'equatorialguinea': 53, 'eritrea': 54,
                            'estonia': 55, 'ethiopia': 56, 'fiji': 57, 'finland': 58, 'france': 59, 'gabon': 60,
                            'gambia': 61, 'georgia': 62, 'germany': 63, 'ghana': 64, 'greece': 65, 'grenada': 66,
                            'guatemala': 67, 'guinea': 68, 'guineabissau': 69, 'guyana': 70, 'haiti': 71,
                            'holyseevaticancitystate': 72, 'honduras': 73, 'hungary': 74, 'iceland': 75, 'india': 76,
                            'indonesia': 77, 'iranislamicrepublicof': 78, 'iraq': 79, 'ireland': 80, 'israel': 81,
                            'italy': 82, 'jamaica': 83, 'japan': 84, 'jordan': 85, 'kazakhstan': 86, 'kenya': 87,
                            'koreasouth': 88, 'kuwait': 89, 'kyrgyzstan': 90, 'laopdr': 91, 'latvia': 92, 'lebanon': 93,
                            'lesotho': 94, 'liberia': 95, 'libya': 96, 'liechtenstein': 97, 'lithuania': 98,
                            'luxembourg': 99, 'macedoniarepublicof': 100, 'madagascar': 101, 'malawi': 102,
                            'malaysia': 103, 'maldives': 104, 'mali': 105, 'malta': 106, 'mauritania': 107,
                            'mauritius': 108, 'mexico': 109, 'moldova': 110, 'monaco': 111, 'mongolia': 112,
                            'montenegro': 113, 'morocco': 114, 'mozambique': 115, 'myanmar': 116, 'namibia': 117,
                            'nepal': 118, 'netherlands': 119, 'newzealand': 120, 'nicaragua': 121, 'niger': 122,
                            'nigeria': 123, 'norway': 124, 'oman': 125, 'pakistan': 126, 'palestinianterritory': 127,
                            'panama': 128, 'papuanewguinea': 129, 'paraguay': 130, 'peru': 131, 'philippines': 132,
                            'poland': 133, 'portugal': 134, 'qatar': 135, 'republicofkosovo': 136, 'romania': 137,
                            'russianfederation': 138, 'rwanda': 139, 'saintkittsandnevis': 140, 'saintlucia': 141,
                            'saintvincentandgrenadines': 142, 'sanmarino': 143, 'saotomeandprincipe': 144,
                            'saudiarabia': 145, 'senegal': 146, 'serbia': 147, 'seychelles': 148, 'sierraleone': 149,
                            'singapore': 150, 'slovakia': 151, 'slovenia': 152, 'somalia': 153, 'southafrica': 154,
                            'southsudan': 155, 'spain': 156, 'srilanka': 157, 'sudan': 158, 'suriname': 159,
                            'swaziland': 160, 'sweden': 161, 'switzerland': 162, 'syrianarabrepublicsyria': 163,
                            'taiwanrepublicofchina': 164, 'tajikistan': 165, 'tanzaniaunitedrepublicof': 166,
                            'thailand': 167, 'timorleste': 168, 'togo': 169, 'trinidadandtobago': 170, 'tunisia': 171,
                            'turkey': 172, 'uganda': 173, 'ukraine': 174, 'unitedarabemirates': 175,
                            'unitedkingdom': 176, 'unitedstatesofamerica': 177, 'uruguay': 178, 'uzbekistan': 179,
                            'venezuelabolivarianrepublic': 180, 'vietnam': 181, 'westernsahara': 182, 'yemen': 183,
                            'zambia': 184, 'zimbabwe': 185}
        self.string_corona_countries_1 = "Afghanistan, Albania, Algeria, Andorra, Angola, Antigua and Barbuda, Argentina, Armenia, Australia, Austria, Azerbaijan, Bahamas, Bahrain, Bangladesh, Barbados, Belarus, Belgium, Belize, Benin, Bhutan, Bolivia, Bosnia and Herzegovina, Botswana, Brazil, Brunei Darussalam, Bulgaria, Burkina Faso, Burundi, Cambodia, Cameroon, Canada, Cape Verde, Central African Republic, Chad, Chile, China, Colombia, Comoros, Congo (Brazzaville), Congo (Kinshasa), Costa Rica, Croatia, Cuba, Cyprus, Czech Republic, Côte d'Ivoire, Denmark, Djibouti, Dominica, Dominican Republic, Ecuador, Egypt, El Salvador, Equatorial Guinea, Eritrea, Estonia, Ethiopia, Fiji, Finland, France, Gabon, Gambia, Georgia, Germany, Ghana, Greece, Grenada, Guatemala, Guinea, Guinea-Bissau, Guyana, Haiti, Holy See (Vatican City State), Honduras, Hungary, Iceland, India, Indonesia, Iran, Islamic Republic of, Iraq, Ireland, Israel, Italy, Jamaica, Japan, Jordan, Kazakhstan, Kenya, Korea (South), Kuwait, Kyrgyzstan, Lao PDR, Latvia, Lebanon, Lesotho, Liberia, Libya, Liechtenstein, Lithuania, Luxembourg, Macedonia, Republic of, Madagascar, Malawi, Malaysia, Maldives"
        self.string_corona_countries_2 = "Mali, Malta, Mauritania, Mauritius, Mexico, Moldova, Monaco, Mongolia, Montenegro, Morocco, Mozambique, Myanmar, Namibia, Nepal, Netherlands, New Zealand, Nicaragua, Niger, Nigeria, Norway, Oman, Pakistan, Palestinian Territory, Panama, Papua New Guinea, Paraguay, Peru, Philippines, Poland, Portugal, Qatar, Republic of Kosovo, Romania, Russian Federation, Rwanda, Saint Kitts and Nevis, Saint Lucia, Saint Vincent and Grenadines, San Marino, Sao Tome and Principe, Saudi Arabia, Senegal, Serbia, Seychelles, Sierra Leone, Singapore, Slovakia, Slovenia, Somalia, South Africa, South Sudan, Spain, Sri Lanka, Sudan, Suriname, Swaziland, Sweden, Switzerland, Syrian Arab Republic (Syria), Taiwan, Republic of China, Tajikistan, Tanzania, United Republic of, Thailand, Timor-Leste, Togo, Trinidad and Tobago, Tunisia, Turkey, Uganda, Ukraine, United Arab Emirates, United Kingdom, United States of America, Uruguay, Uzbekistan, Venezuela (Bolivarian Republic), Viet Nam, Western Sahara, Yemen, Zambia, Zimbabwe"

    @commands.command(pass_context=True)
    async def weather(self, ctx, *, city):

        url = "http://api.openweathermap.org/data/2.5/weather?q=" + city + "&APPID=" + self.Config[
            "openweather_api_key"]
        response = requests.get(url).json()

        try:
            if response["message"] == "city not found":
                url = "http://api.openweathermap.org/data/2.5/weather?q=" + self.countries[city.title()] + "&APPID=" + \
                      self.Config[
                          "openweather_api_key"]
                response = requests.get(url).json()
                if response["message"] == "city not found":
                    await ctx.send(utils.format_message(ctx, "'" + city + "' is not a valid city or country"))
        except KeyError:
            pass


        print(self.cities[city.lower()])

        try:
            city_id = str(self.cities[city.lower()]["id"])
            country = str(self.cities[city.lower()]["country"]).upper()
        except KeyError:
            city_id = str(self.cities[self.countries[city.title()].lower()]["id"])
            country = str(self.cities[self.countries[city.title()].lower()]["country"]).upper()

        embed = discord.Embed(
            title="Weather in " + city.title() + ", " + country,
            description="",
            colour=discord.Colour(value=eval(self.Config["bot_colour"])),
            url="https://openweathermap.org/city/" + city_id
        )

        embed.set_thumbnail(url="http://openweathermap.org/img/wn/" + response["weather"][0]["icon"] + "@4x.png")

        embed.add_field(name="Temperature", value=str(round(response["main"]["temp"] - 273.15, 1)) + "°C", inline=True)
        embed.add_field(name="Feels like", value=str(round(response["main"]["feels_like"] - 273.15, 1)) + "°C",
                        inline=True)
        embed.add_field(name="Humidity", value=str(response["main"]["humidity"]) + "%", inline=True)
        embed.add_field(name="Sky", value=self.weather_types[response["weather"][0]["icon"][:-1]].title(), inline=True)

        await ctx.send(embed=embed)

    @commands.command(pass_content=True)
    async def covid(self, ctx, *, country=None):

        if str(country).lower() == "countries":
            await ctx.send(utils.format_message(ctx, "List of countries:\n" + self.string_corona_countries_1))
            await ctx.send(utils.format_message(ctx, self.string_corona_countries_2))
            return

        elif country is not None and re.sub('[^A-Za-z0-9]+', '', country).lower() not in self.corona_countries.keys():
            await ctx.send(utils.format_message(ctx,
                                   "That is not a valid country. To get a list of all countries, use `" + self.Config["bot_prefix"] + inspect.getframeinfo(
                                       inspect.currentframe()).function + " countries`\n\nIf you don't specify a country, this command will show the worldwide statistics"))
            return

        data = eval(urlopen(url="https://api.covid19api.com/summary").read())
        date = data["Date"][:10]

        if country is None:
            data = data["Global"]
            name = "Worldwide"
        else:
            data = data["Countries"][self.corona_countries[re.sub('[^A-Za-z0-9]+', '', country).lower()]]
            name = data["Country"]

        embed = discord.Embed(
            title=name + " COVID-19 statistics",
            description="As of " + date,
            colour=discord.Colour(value=eval(self.Config["bot_colour"]))
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
