# coding: utf-8
import ytmusicapi

ytmusic = ytmusicapi.YTMusic("/home/hamish/src/hq/etc/ytmusic_headers_auth.json")

playlists = ytmusic.get_library_playlists()

things = next(p for p in playlists if p["title"] == "Things")

things = ytmusic.get_playlist(things["playlistId"], limit=1000)

tracks_by_chubb = [track for track in things["tracks"] if any("Chubb" in artist["name"] for artist in track["artists"])]

print(tracks_by_chubb)
