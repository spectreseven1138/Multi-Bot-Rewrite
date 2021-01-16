import lyricsgenius

search_term = input("Input search term... ")



genius = lyricsgenius.Genius("X4UK4ESbWR5aeES_s5EtBH1hpaUfook6Buc9ERqJZPlmy2FeNtIxWePWDCI10WbD")

song = genius.search_song(search_term)
print(song.lyrics)
print(song.url)
print(song.album)
print(song.artist)
print(song.song_art_image_url)
print(song.year)