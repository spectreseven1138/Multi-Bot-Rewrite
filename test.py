import json

f = open("openweather_data/cities.json", "r")

data = json.loads(f.read())
f.close()


OUTPUT = {}


for item in data:

    item.pop("state", None)
    item.pop("coord", None)
    item.pop("id", None)

    OUTPUT[item.pop("name", None)] = item
    print(item)

f = open("openweather_data/cities.json", "w")

f.write(json.dumps(OUTPUT))

f.close()