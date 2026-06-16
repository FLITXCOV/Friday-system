import webbrowser
import urllib.parse
import subprocess
import time
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Initialize the MCP Server
mcp = FastMCP("Friday-System-Host")

# ===========================================================================
# SPOTIFY WEB API CLIENT
# ===========================================================================

def _get_spotify() -> spotipy.Spotify:
    """Returns an authenticated Spotify client using the Web API."""
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri="http://127.0.0.1:8888/callback",
        scope="user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private playlist-read-collaborative user-library-read",
        open_browser=True,
        cache_path=".spotify_cache"
    ))

# ===========================================================================
# HARDWARE CONTROLS
# ===========================================================================

@mcp.tool()
def change_brightness(level: int) -> str:
    """
    Sets the screen brightness on laptops that support WMI brightness control.
    Accepts 0 to 100.
    """
    safe_level = max(0, min(100, level))

    script = (
        f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
        f".WmiSetBrightness(1, {safe_level})"
    )
    result = subprocess.run(
        ["powershell", "-Command", script],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        return f"Brightness command failed. Error: {result.stderr.strip()}"
    return f"Screen brightness set to {safe_level}%."

@mcp.tool()
def set_volume(level: int) -> str:
    """Sets system volume (0 to 100)."""
    try:
        import comtypes
        comtypes.CoInitialize()
        from pycaw.pycaw import AudioUtilities

        safe_level = max(0, min(100, level))
        speakers = AudioUtilities.GetSpeakers()
        volume = speakers.EndpointVolume
        volume.SetMute(0, None)
        volume.SetMasterVolumeLevelScalar(safe_level / 100.0, None)
        return f"System volume set to {safe_level}%."
    except Exception as e:
        return f"Could not set volume: {e}"

@mcp.tool()
def toggle_mute() -> str:
    """Toggles system mute."""
    try:
        import comtypes
        comtypes.CoInitialize()
        from pycaw.pycaw import AudioUtilities

        speakers = AudioUtilities.GetSpeakers()
        volume = speakers.EndpointVolume
        current_mute = volume.GetMute()
        volume.SetMute(0 if current_mute else 1, None)
        return "System unmuted." if current_mute else "System muted."
    except Exception as e:
        return f"Could not toggle mute: {e}"

# ===========================================================================
# NAVIGATION & MAPS
# ===========================================================================

@mcp.tool()
def locate_on_earth(location: str) -> str:
    """Opens Google Earth and flies directly to the specified city, state, or country."""
    try:
        safe_location = urllib.parse.quote(location)
        url = f"https://earth.google.com/web/search/{safe_location}"
        webbrowser.open(url)
        return f"Opening Google Earth to show {location}."
    except Exception as e:
        return f"Failed to open Google Earth: {e}"

# ===========================================================================
# MEDIA & ENTERTAINMENT — SPOTIFY (Web API)
# ===========================================================================

@mcp.tool()
def open_spotify() -> str:
    """Opens the Spotify desktop application."""
    try:
        subprocess.Popen("start spotify:", shell=True)
        return "Spotify is opening."
    except Exception as e:
        return f"Could not open Spotify: {e}"

@mcp.tool()
def play_spotify(query: str, search_type: str = "track") -> str:
    """
    Searches Spotify and plays a track, album, or playlist.
    search_type must be one of: 'track', 'album', 'playlist'.
    If searching for a playlist, it checks the user's personal library first.
    """
    try:
        sp = _get_spotify()

        # Validate search_type
        if search_type not in ["track", "album", "playlist"]:
            search_type = "track"

        # Get any available device (active or not)
        devices = sp.devices()
        all_devices = devices.get("devices", [])

        if not all_devices:
            import subprocess
            import time
            subprocess.Popen("start spotify:", shell=True)
            for attempt in range(6):
                time.sleep(3)
                devices = sp.devices()
                all_devices = devices.get("devices", [])
                if all_devices:
                    break

        if not all_devices:
            return f"Found '{query}' but Spotify didn't start in time. Try again in a few seconds, boss."

        active = [d for d in all_devices if d["is_active"]]
        device = active[0] if active else all_devices[0]
        device_id = device["id"]

        # 1. Check for "Liked Songs" (Special Case)
        if search_type == "playlist" and query.lower() in ["liked songs", "my liked songs", "favorites"]:
            results = sp.current_user_saved_tracks(limit=50)
            tracks = results["items"]
            if not tracks:
                return "You have no liked songs saved on Spotify."
            uris = [item["track"]["uri"] for item in tracks]
            sp.start_playback(device_id=device_id, uris=uris)
            return "Playing your Liked Songs on Spotify."

        # 2. Check Personal Playlists
        if search_type == "playlist":
            user_playlists = sp.current_user_playlists(limit=50)
            for pl in user_playlists["items"]:
                if pl and query.lower() in pl["name"].lower():
                    sp.start_playback(device_id=device_id, context_uri=pl["uri"])
                    return f"Playing your playlist '{pl['name']}' on Spotify."

        # 3. Fallback to Global Search
        results = sp.search(q=query, type=search_type, limit=1)
        items = results[f"{search_type}s"]["items"]

        if not items:
            return f"Could not find any {search_type} matching '{query}' on Spotify."

        item = items[0]
        item_uri = item["uri"]
        item_name = item["name"]

        if search_type == "track":
            # Play the track within its album context so the queue is populated
            album_uri = item["album"]["uri"]
            sp.start_playback(device_id=device_id, context_uri=album_uri, offset={"uri": item_uri})
            artist = item["artists"][0]["name"]
            return f"Playing track '{item_name}' by {artist} on Spotify."
        else:
            sp.start_playback(device_id=device_id, context_uri=item_uri)
            return f"Playing {search_type} '{item_name}' on Spotify."

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Spotify playback error: {str(e)[:100]}"

@mcp.tool()
def control_spotify(action: str) -> str:
    """Controls Spotify (play, pause, next, previous)."""
    try:
        sp = _get_spotify()
        action = action.lower().strip()

        # Get device
        devices = sp.devices().get("devices", [])
        if not devices:
            return "No Spotify device found. Open Spotify first."
            
        active = [d for d in devices if d["is_active"]]
        device_id = active[0]["id"] if active else devices[0]["id"]

        if action == "play":
            sp.start_playback(device_id=device_id)
            return "Playback resumed."
        elif action in ["pause", "stop"]:
            sp.pause_playback(device_id=device_id)
            return "Playback paused."
        elif action in ["next", "skip"]:
            sp.next_track(device_id=device_id)
            return "Skipped to next track."
        elif action in ["previous", "back"]:
            sp.previous_track(device_id=device_id)
            return "Went back to previous track."
        else:
            return f"Unknown action '{action}'."

    except spotipy.exceptions.SpotifyException as e:
        return f"Spotify error: {str(e)[:100]}"
    except Exception as e:
        return f"Playback error: {str(e)[:100]}"

@mcp.tool()
def get_current_song() -> str:
    """Returns the currently playing song on Spotify."""
    try:
        sp = _get_spotify()
        current = sp.current_playback()

        if not current or not current.get("is_playing"):
            return "Nothing is currently playing on Spotify."

        track = current["item"]
        song = track["name"]
        artist = track["artists"][0]["name"]
        return f"Currently playing '{song}' by {artist}."

    except Exception as e:
        return f"Could not get current track: {str(e)[:80]}"

@mcp.tool()
def open_youtube(search_query: str = "") -> str:
    """Opens YouTube. If a search_query is provided, searches for that video."""
    if search_query:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(search_query)}"
        webbrowser.open(url)
        return f"Opened YouTube search for '{search_query}'."
    else:
        webbrowser.open("https://www.youtube.com")
        return "YouTube is now open on the main screen."

@mcp.tool()
def open_website(url: str) -> str:
    """
    Opens an arbitrary website URL in the default browser. 
    Make sure to provide a full URL (e.g., 'https://www.instagram.com', 'https://www.linkedin.com').
    """
    try:
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)
        return f"Opened {url} in the browser."
    except Exception as e:
        return f"Failed to open website: {e}"

# ===========================================================================
# SYSTEM & SECURITY
# ===========================================================================

@mcp.tool()
def take_screenshot() -> str:
    """Takes a screenshot of the entire screen and saves it to the Desktop."""
    try:
        import pyautogui
        import os
        from datetime import datetime
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        filename = datetime.now().strftime("Screenshot_%Y-%m-%d_%H%M%S.png")
        filepath = os.path.join(desktop, filename)
        pyautogui.screenshot(filepath)
        return f"Screenshot taken and saved to your desktop at {filepath}."
    except ImportError:
        return "PyAutoGUI is not installed. Run 'uv pip install pyautogui'."
    except Exception as e:
        return f"Failed to take screenshot: {e}"

@mcp.tool()
def get_directions(destination: str) -> str:
    """Opens Google Maps in the browser showing a driving route to the destination from the user's current location."""
    try:
        import urllib.parse
        safe_dest = urllib.parse.quote(destination)
        url = f"https://www.google.com/maps/dir/?api=1&destination={safe_dest}&travelmode=driving"
        webbrowser.open(url)
        return f"Opened Google Maps driving directions to {destination}."
    except Exception as e:
        return f"Failed to open Google Maps: {e}"

@mcp.tool()
def close_current_tab() -> str:
    """Closes the currently active browser tab or window by pressing Ctrl+W."""
    try:
        import pygetwindow as gw
        active_window = gw.getActiveWindow()
        if active_window and "friday-ui" in active_window.title.lower():
            return "I am currently the active tab, boss. I cannot close myself."
            
        import pyautogui
        pyautogui.hotkey('ctrl', 'w')
        return "Closed the current tab."
    except ImportError:
        import pyautogui
        pyautogui.hotkey('ctrl', 'w')
        return "Closed the current tab (PyGetWindow not installed, skipping safety check)."
    except Exception as e:
        return f"Failed to close tab: {e}"

@mcp.tool()
def terminate_friday() -> str:
    """Forcefully terminates all F.R.I.D.A.Y. background processes and shuts down the system."""
    try:
        subprocess.run("taskkill /F /IM python.exe /T", shell=True)
        subprocess.run("taskkill /F /IM node.exe /T", shell=True)
        return "Terminating all systems. Goodbye, boss."
    except Exception as e:
        return f"Failed to terminate systems: {e}"

@mcp.tool()
def send_whatsapp(contact_name: str, message: str, attachment_path: str = "") -> str:
    """
    Automates sending a WhatsApp message to a contact.
    Requires WhatsApp Desktop to be installed and logged in.
    Optionally sends an image attachment.
    """
    import pyautogui
    import time
    import subprocess
    import os

    try:
        # Copy image to clipboard if attachment provided
        if attachment_path and os.path.exists(attachment_path):
            script = f"""
            Add-Type -AssemblyName System.Windows.Forms
            Add-Type -AssemblyName System.Drawing
            $img = [System.Drawing.Image]::FromFile('{attachment_path}')
            [System.Windows.Forms.Clipboard]::SetImage($img)
            """
            subprocess.run(["powershell", "-Command", script])

        # 1. Open WhatsApp
        subprocess.Popen("start whatsapp:", shell=True)
        time.sleep(4) # Wait for it to open

        # 2. Search for contact (Ctrl+F)
        pyautogui.hotkey('ctrl', 'f')
        time.sleep(1)
        pyautogui.typewrite(contact_name)
        time.sleep(2)
        pyautogui.press('enter')
        time.sleep(1)

        # 3. Paste attachment if any
        if attachment_path and os.path.exists(attachment_path):
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(1.5)
            pyautogui.press('enter')
            time.sleep(1)

        # 4. Type message and send
        if message:
            pyautogui.typewrite(message)
            time.sleep(0.5)
            pyautogui.press('enter')

        return f"Automated WhatsApp message sent to {contact_name}."
    except Exception as e:
        return f"WhatsApp automation failed: {e}"

# ===========================================================================
# ENTRY POINT
# ===========================================================================

if __name__ == "__main__":
    print("F.R.I.D.A.Y. Local MCP Server initializing on port 8000...")
    mcp.run(transport='sse')