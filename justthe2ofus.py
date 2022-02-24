"""
Prerequisites

    pip3 install spotipy Flask Flask-Session

    // from your [app settings](https://developer.spotify.com/dashboard/applications)
    export SPOTIPY_CLIENT_ID=client_id_here
    export SPOTIPY_CLIENT_SECRET=client_secret_here
    export SPOTIPY_REDIRECT_URI='http://yourserverip:8080' // must contain a port
    // SPOTIPY_REDIRECT_URI must be added to your [app settings](https://developer.spotify.com/dashboard/applications)
    OPTIONAL
    // in development environment for debug output
    export FLASK_ENV=development
    // so that you can invoke the app outside of the file's directory include
    export FLASK_APP=/path/to/spotipy/examples/app.py

    // on Windows, use `SET` instead of `export`

Run app.py

    python3 app.py OR python3 -m flask run
    NOTE: If receiving "port already in use" error, try other ports: 5000, 8090, 8888, etc...
        (will need to be updated in your Spotify app and SPOTIPY_REDIRECT_URI variable)
"""

import os
from flask import Flask, session, request, redirect, render_template
from flask_session import Session
import spotipy
import uuid
# import json
import csv
import glob

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(64)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
Session(app)

caches_folder = './.spotify_caches/'
if not os.path.exists(caches_folder):
    os.makedirs(caches_folder)


def session_cache_path():
    return caches_folder + session.get('uuid')


songs_url_list = ['https://open.spotify.com/track/2NBQmPrOEEjA8VbeWOQGxO']
song_count = int(1500)


def list_split(listA, n):
    for x in range(0, len(listA), n):
        every_chunk = listA[x: n+x]

        if len(every_chunk) < n:
            every_chunk = every_chunk + \
                [None for y in range(n-len(every_chunk))]
        yield every_chunk


@app.route('/')
def index():
    if not session.get('uuid'):
        # Step 1. Visitor is unknown, give random ID
        session['uuid'] = str(uuid.uuid4())

    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path())
    auth_manager = spotipy.oauth2.SpotifyOAuth(scope='playlist-modify-private,user-library-read,playlist-modify-public',
                                               cache_handler=cache_handler,
                                               show_dialog=True,
                                               client_id='90259c6fcaa847d8b3a2e8608dd14e5c',
                                               redirect_uri='http://139.179.184.73:8080',
                                               client_secret='a354471cfe744280a64040c867251170')

    if request.args.get("code"):
        # Step 3. Being redirected from Spotify auth page
        auth_manager.get_access_token(request.args.get("code"))
        return redirect('/')

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        # Step 2. Display sign in link when no token
        auth_url = auth_manager.get_authorize_url()
        return f'<h2><big><big><big><big><big><a href="{auth_url}">Sign in</a></h2>'

# Step 4. Signed in, display data#####
    spotify = spotipy.Spotify(auth_manager=auth_manager)

# =============================================================================
#     return f'<h2>Hi {spotify.me()["display_name"]}, ' \
#         f'<big><a href="/sign_out">[sign out]<a/></big></h2>' \
#         f'<a href="/create_code">Create Code</a> / ' \
#         f'<a href="/selectuser">Select User</a>' \
# =============================================================================
    name = spotify.me()["display_name"]
    return render_template("index.html", name=name)


@app.route('/sign_out')
def sign_out():
    try:
        # Remove the CACHE file (.cache-test) so that a new user can authorize.
        os.remove(session_cache_path())
        session.clear()
    except OSError as e:
        print("Error: %s - %s." % (e.filename, e.strerror))
    return redirect('/')


@app.route('/selectuser')
def choose_user():
    list_of_csv_files = glob.glob("*.csv")
    usernames = []
    list_of_csv_files_nospace = []
    for i in range(len(list_of_csv_files)):
        username = str(list_of_csv_files[i]).split("&")[0]
        usernames.append(username)
        # print(list_of_csv_files)
    for nospace in list_of_csv_files:
        list_of_csv_files_nospace.append(nospace)
    return render_template("showlistt.html", len=len(list_of_csv_files), list_of_csv_files_nospace=list_of_csv_files_nospace, usernames=usernames)


songs_in_common = []
songdetails_list = []


@app.route('/<filename>')  # userselected
def user_selected(filename):
    if filename == "favicon.ico":
        pass
    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path())
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler,
                                               client_id='90259c6fcaa847d8b3a2e8608dd14e5c',
                                               redirect_uri='http://139.179.184.73:8080',
                                               client_secret='a354471cfe744280a64040c867251170')
    spotify = spotipy.Spotify(auth_manager=auth_manager)

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect('/')

    songs_in_common = []
    songdetails_list = []
    songs_url_list.clear()
    with open(filename, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=' ', quotechar='|')
        songs_url_list.clear()
        for row in reader:
            for i in range(0, len(row)):
                songs_url_list.append(row[i])
        username = filename.split("&")[0]

        # print(songs_url_list)
        del songs_url_list[0]  # delete user name from list

        songs_in_common.clear()
        url_chunks_list = list(list_split(songs_url_list, 49))
        for url_chunks in url_chunks_list:
            url_chunks = [i for i in url_chunks if i]

            # print(url_chunks)
            contains = spotify.current_user_saved_tracks_contains(url_chunks)
            for n in range(len(contains)):

                if contains[n]:
                    songs_in_common.append(url_chunks[n])
                    songdetails = spotify.track(songs_in_common[-1])
                    songdetails_list.append(songdetails['artists'][0]['name'] +
                                            " – " + songdetails['name'] + "–")
        with open("&" + 'commonsongs.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=' ',
                                quotechar='|', quoting=csv.QUOTE_MINIMAL)
            # songs_url_list.insert(0, user_name)
            writer.writerow(songs_in_common)
        selectedusername = username
    return render_template("usuerselectedd.html", len=len(songs_in_common), songs_in_common=songs_in_common, username=username, selectedusername=selectedusername, songdetails_list=songdetails_list)
    # return str(songs_in_common)


@app.route('/create_code')
def get_userliked():
    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path())
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler,
                                               client_id='90259c6fcaa847d8b3a2e8608dd14e5c',
                                               redirect_uri='http://139.179.184.73:8080',
                                               client_secret='a354471cfe744280a64040c867251170')
    spotify = spotipy.Spotify(auth_manager=auth_manager)

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect('/')

    results = spotify.current_user_saved_tracks(
        limit=1, offset=10000, market=None)
    # print(results)
    amount = results['total']
    amount = song_count if amount > song_count else print()
    doneamount = 0
    while(doneamount <= amount):
        results = spotify.current_user_saved_tracks(
            limit=20, offset=doneamount, market=None)
        for idx, item in enumerate(results['items']):
            track = item['track']
            song_url = track['external_urls']['spotify']
            #print(idx+doneamount, track['artists'][0]['name'], " – ", track['name'], "–", song_url)
            songs_url_list.append(song_url)
        doneamount = doneamount+20
    user_details = spotify.current_user()
    user_name = spotify.me()["display_name"]
    # save song library as csv
    with open(user_name + "&" + user_details['id']+'.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=' ',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
        # songs_url_list.insert(0, user_name)
        writer.writerow(songs_url_list)

    # for line in len(songs_url_list):
    return render_template("donee.html")


@app.route('/create_playlist/<selectedusername>')
def save_as_playlist(selectedusername):
    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path())
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler,
                                               client_id='90259c6fcaa847d8b3a2e8608dd14e5c',
                                               redirect_uri='http://139.179.184.73:8080',
                                               client_secret='a354471cfe744280a64040c867251170')
    spotify = spotipy.Spotify(auth_manager=auth_manager)

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect('/')
    with open("&commonsongs.csv", 'r', newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=' ', quotechar='|')
        songs_in_common.clear()
        for row in reader:
            for i in range(0, len(row)):
                songs_in_common.append(row[i])

    user_details = spotify.current_user()
    user_name = str(spotify.me()["display_name"]).split(' ')[0]
    name = selectedusername.split("%20")[0]+'++'+user_name
    created_playlist = spotify.user_playlist_create(
        user_details["id"], name, public=True, collaborative=False, description='')
    #songs_in_commonn = list(dict.fromkeys(songs_in_common))
    spotify.user_playlist_add_tracks(
        user_details["id"], created_playlist["id"], songs_in_common, position=None)
    link = created_playlist
    print(link)
    return str(songs_url_list, link=link)


if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True, port=8080, debug=False)
