import urllib.parse as urlparse
from http.client import InvalidURL

import requests
from discord.channel import DMChannel
import commentjson as json

f = open("bot_config.json", "r")
Config = json.loads(f.read())
f.close()


def parse(string_to_parse: str, split_chars: list = (" ")):
    if string_to_parse is None:
        return []

    out = []
    current = ""

    for char in string_to_parse:
        if char in split_chars:
            if current != "":
                out.append(current)
                current = ""
        else:
            current = current + char

    if current != "":
        out.append(current)

    return out


def parse_quotes(string_to_parse: str, quote_types: list = None):
    if string_to_parse is None:
        return [[], []]
    elif quote_types is None:
        quote_types = ['""']

    exclude_non_quoted = []
    include_non_quoted = []

    exclude = ""
    include = ""

    adding = False

    for char in string_to_parse:
        if adding is not False:
            if char == quote_types[adding][1]:

                adding = False
                exclude_non_quoted.append(exclude + char)
                exclude = ""

                include_non_quoted.append(include + char)
                include = ""

            else:
                exclude = exclude + char
                include = include + char
        else:
            for i, type in enumerate(quote_types):
                if char == type[0]:
                    adding = i
                    exclude = char

                    if include != "":
                        include_non_quoted.append(include)

                    include = char
                    break

            if adding is False:
                include = include + char

    if exclude != "":
        exclude_non_quoted.append(exclude)
    if include != "":
        include_non_quoted.append(include)

    return [exclude_non_quoted, include_non_quoted]


def parse_url(url):
    parsed = {}

    try:
        try:
            url = requests.get(url).url
        except:
            url = requests.get("http://" + url).url
    except:
        pass
    else:
        try:
            parsed = urlparse.parse_qs(urlparse.urlparse(url).query)
        except InvalidURL:
            pass

    return parsed


def format_message(ctx, msg: str, ping=None):

    if ping:
        return ctx.message.author.mention + " | " + msg
    elif ping is None:
        if is_dmchannel(ctx):
            return msg
        else:
            return ctx.message.author.mention + " | " + msg
    else:
        if is_dmchannel(ctx):
            return msg
        else:
            return ctx.message.author.name + " | " + msg


def is_dmchannel(ctx):
    return isinstance(ctx.channel, DMChannel)


async def incorrect_syntax(ctx, command):

    await ctx.send(format_message(ctx,
                                  "That is not the correct usage of this command\nFor information about this command works, use `" +
                                  Config["bot_prefix"] + "help " + command + "`"))
