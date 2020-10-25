from discord.channel import DMChannel


def parse(string_to_parse: str, split_chars=(" ")):

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


def format_message(ctx, msg: str):
    if isinstance(ctx.channel, DMChannel):
        return msg
    else:
        return ctx.message.author.mention + " | " + msg