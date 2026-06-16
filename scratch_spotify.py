from mcp_server import _get_spotify

sp = _get_spotify()

# Search
results = sp.search(q="track:treat you better", type="track", limit=1)
track = results["tracks"]["items"][0]
print(f"Found: {track['name']} by {track['artists'][0]['name']}")
print(f"URI: {track['uri']}")

# Get device
devices = sp.devices()
all_devices = devices.get("devices", [])
print(f"Devices: {len(all_devices)}")
if all_devices:
    device = all_devices[0]
    print(f"Using: {device['name']} (active={device['is_active']})")
    sp.start_playback(device_id=device["id"], uris=[track["uri"]])
    print("PLAYING!")
else:
    print("No devices found")
