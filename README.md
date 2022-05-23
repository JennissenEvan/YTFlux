# YTFlux
A simple python script for downloading and syncing YouTube playlists to a local folder. Mainly intended for use with 
music playlists.

# Features
- All videos are downloaded as .mp4 audio files
- Can use OAuth to download age restricted videos
- Video info, including thumbnail, is attached to audio files as metadata
- Videos removed from the playlist are automatically deleted on update
- All downloaded files are stored in a database file, removed/corrupted files are automatically redownloaded
- Videos that become private, unavailable, etc. are documented and kept

# Usage
On the first run, input the link to the desired public or unlisted playlist. Then, verify with OAuth (if desired). The 
script will then download all the videos and save them as .mp4 audio files in the _music_ folder. To update the folder, 
simply run the script again and any new videos will be downloaded. 

To fully reset the script, delete _playlist.db_ and  _music_.

The script can be packaged into a .exe via Pyinstaller by running _setup.py_

# Dependencies
The following packages can be installed from pip.
- pytube
- mutagen
- Pillow
- requests
- urllib3
- pyinstaller (optional, for building to executable)
