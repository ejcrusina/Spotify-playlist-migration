""" 
This file migrates the song files saved locally into Spotify by adding their corresponding tracks in a playlist.
"""

import os
import time
import numpy as np
import pandas as pd
from tqdm import tqdm

import spotipy

from fuzzywuzzy import fuzz
from tinytag import TinyTag


def create_playlist(username, playlist_name):
    """ 
    Creates empty playlist in account
    """
    sp.user_playlist_create(username, name=playlist_name)
    return print("Playlist Created.")


def get_trackIDs(
    local_music_df, 
    query_limit=5,
    artist_similarity_thres=90, 
    song_similarity_thres=90
):
    """ 
    Gets Spotify trackID of songs with query match in Spotify's collection of tracks
    """
    track_ids = []
    song_without_track = dict()

    for i in tqdm(range(len(local_music_df))): # Adds progress bar
        # Get query responses
        results = sp.search(q=f"{local_music_df['title'][i]} {local_music_df['artist'][i]} ", limit=query_limit, type='track') 

        # If track isn't on spotify as queried, go to next track
        if results['tracks']['total'] == 0:
            song_without_track[local_music_df['title'][i]] = local_music_df['artist'][i]
        else:
            # Iterate thru possible matches of a given track
            for j in range(len(results['tracks']['items'])):
                # Fuzzy string matching of artist
                queried_artist = results['tracks']['items'][j]['artists'][0]['name']
                target_artist = local_music_df['artist'][i]
                artist_similarity_score = fuzz.partial_ratio(queried_artist, target_artist)

                # Fuzzy string matching of song title
                queried_song = results['tracks']['items'][j]['name']
                target_song = local_music_df['title'][i]
                song_similarity_score = fuzz.partial_ratio(queried_song, target_song)

                # Save track if similarity is above thres
                if artist_similarity_score > artist_similarity_thres and song_similarity_score > song_similarity_thres:
                    track_ids.append(results['tracks']['items'][j]['id']) #append track id
                    break # Avoids duplicates of the same track (e.g. different versions)
                else:
                    continue
            
        time.sleep(3) # Add delay per query
                
    # Get list of songs without tracks in Spotify
    no_tracks_list = pd.DataFrame(song_without_track.items(), columns=['title', 'artist'])            
    
    print("Got TrackIDs!")
    return track_ids, no_tracks_list


def get_playlistID(username, playlist_name):
    """ 
    Gets playlistID of existing playlist
    """
    playlist_id = ''
    playlists = sp.user_playlists(username)
    for playlist in playlists['items']:  # Iterate through playlists present in acct
        if playlist['name'] == playlist_name:  # Filter for newly created playlist
            playlist_id = playlist['id']
    print("Got Playlist ID.")
    return playlist_id


## Get OAuth token with scope "playlist-modify-public" in this link: 
## https://developer.spotify.com/console/post-playlists/
token='####'
sp = spotipy.Spotify(auth=token)


# Get all music directories in Music folder of local machine
root_dir = r"C:...\Music"
music_dir_all_files = []
for path, subdirs, files in os.walk(root_dir):
    for name in files:
        music_dir_all_files.append(os.path.join(path, name))

# Get directories that are not music files (e.g. init or jpg) by checking their tags
# NOTE - this script will only migrate all local music files with metadata (i.e. tags for artist, title, etc.)
other_files = []
for filename in music_dir_all_files:
    try:
        TinyTag.get(filename) 
    except:
        other_files.append(filename)

# Get all music files by excluding other files 
music_files = [filename for filename in music_dir_all_files if filename not in other_files]
# Get metadata of mp3 or flac files
music_metadata = [TinyTag.get(music_file) for music_file in music_files]

# Get music title and artists from metadata and load as df
song_titles = [metadata.title for metadata in music_metadata]
artists = [metadata.artist for metadata in music_metadata]
local_music_df = pd.DataFrame.from_dict({
    'title':song_titles, 
    'artist':artists
})


# Create playlist
username = "User"
playlist_name = "Local music library"
create_playlist(username, playlist_name)

# Get track ids of matched spotify tracks for each music file
track_ids, no_tracks_list = get_trackIDs(local_music_df)
track_ids = list(dict.fromkeys(track_ids)) # Removes duplicates
print(f"{np.round(len(track_ids)*100/len(music_files),2)}% in music list have matching spotify track")

# Get ID of created playlist
playlist_id = get_playlistID(username, playlist_name)

# Populate playlist with music files that have matched tracks
# NOTE - Populate 100 tracks at a time due to request limit of API
for i in range(len(track_ids)//100 + 1):
    if i != len(track_ids)//100:
        sp.user_playlist_add_tracks(username, playlist_id, track_ids[i*100:(i+1)*100])
    else: # For remaining rows < 100
        sp.user_playlist_add_tracks(username, playlist_id, track_ids[i*100:])
