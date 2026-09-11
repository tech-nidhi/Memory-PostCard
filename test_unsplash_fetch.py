import urllib.request

theme_photos = {
    "snowyMorning": "https://images.unsplash.com/photo-1517299321609-52687d1bc55a?w=1152&h=768&fit=crop&q=85&auto=format",
    "rainyDay": "https://images.unsplash.com/photo-1519692933481-e162a57d6721?w=1152&h=768&fit=crop&q=85&auto=format",
    "cityLights": "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?w=1152&h=768&fit=crop&q=85&auto=format",
    "sunsetEscape": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1152&h=768&fit=crop&q=85&auto=format",
    "autumnPath": "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=1152&h=768&fit=crop&q=85&auto=format",
    "mountainCalling": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1152&h=768&fit=crop&q=85&auto=format",
    "cozyEvening": "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=1152&h=768&fit=crop&q=85&auto=format",
    "vintageVibes": "https://images.unsplash.com/photo-1526772662000-3f88f10405ff?w=1152&h=768&fit=crop&q=85&auto=format",
    "watercolorDream": "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=1152&h=768&fit=crop&q=85&auto=format",
    "monsoonMemories": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1152&h=768&fit=crop&q=85&auto=format"
}

for key, url in theme_photos.items():
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            print(f"SUCCESS {key}: {len(data)} bytes ({resp.headers.get('Content-Type')})")
    except Exception as e:
        print(f"FAILED {key}: {str(e)}")
