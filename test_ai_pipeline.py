import urllib.parse
import urllib.request
import json

themes_prompts = {
    "snowyMorning": "cinematic high-resolution photograph of a secluded wooden cabin in a snow-covered alpine valley at dawn, surrounded by dense snow-laden pine trees, gentle snow falling through the air, fresh footprints leading from foreground toward cabin, warm amber light glowing through cabin windows, thin smoke rising from chimney, distant snow-covered mountains fading into morning mist, realistic winter textures, detailed snow, natural atmospheric depth, soft early morning light, professional travel photography, highly detailed, photorealistic",
    "rainyDay": "highly detailed cinematic photograph of a quiet old city street during heavy evening rain, wet pavement covered with reflective puddles, pedestrians carrying dark umbrellas, warm café lights glowing through rain-covered windows, street lamps reflecting across wet road, rain droplets visible in foreground, distant buildings fading into atmospheric mist, realistic water reflections, natural overcast lighting, professional 35mm travel photography, photorealistic, high resolution",
    "cityLights": "high-resolution cinematic nighttime photograph of a busy Tokyo street in Shibuya, dense storefronts covered in illuminated Japanese signage, pedestrians crossing street, taxis and cars moving through intersection, towering buildings disappearing into night, colorful neon reflections across wet pavement after light rain, realistic street lighting, atmospheric depth, detailed architecture, 35mm street photography, photorealistic",
    "sunsetEscape": "cinematic high-resolution photograph of a quiet tropical beach at sunset, orange sun touching horizon, dramatic clouds illuminated with gold and pink light, palm trees silhouetted against sky, gentle waves reflecting sunset colors, a vintage van parked near shoreline, realistic sand texture, long shadows, warm atmospheric haze, professional travel photography, photorealistic, highly detailed",
    "autumnPath": "high-resolution cinematic photograph of a narrow forest path during peak autumn, tall trees covered in vivid orange, amber and red leaves, thousands of fallen leaves covering path, warm afternoon sunlight passing through canopy, subtle mist in distance, detailed bark and foliage textures, natural depth, peaceful nostalgic atmosphere, professional landscape photography, photorealistic",
    "mountainCalling": "breathtaking high-resolution mountain landscape photographed from a hiking trail, enormous green alpine peaks rising into dramatic clouds, a lone hiker standing on rocky viewpoint in foreground for scale, winding trail disappearing into valley, pine forests covering lower slopes, atmospheric mist between distant mountains, natural sunlight, realistic rock and vegetation textures, cinematic professional landscape photography, photorealistic",
    "cozyEvening": "highly detailed cozy wooden cabin interior at night, warm amber table lamp illuminating open book on wooden table, steaming cup of tea beside it, thick knitted blanket on comfortable chair, fireplace glowing softly in background, rain visible through window, warm shadows, rich wood textures, intimate composition, cinematic interior photography, photorealistic, extremely detailed",
    "vintageVibes": "highly detailed 1950s travel photograph of an old European railway station, classic vintage automobile parked outside, period architecture, travelers carrying leather suitcases, old station signage, warm afternoon sunlight, authentic mid-century clothing, subtle analog film grain, realistic imperfections, natural composition, historical travel photography aesthetic",
    "watercolorDream": "masterpiece fine art watercolor painting of a serene wildflower meadow surrounding a quiet lake and rolling hills at sunrise, visible wet-on-wet paint washes, delicate brush strokes, cold press paper texture, soft pastel color bleeds, impressionistic painterly atmosphere, hand-painted details, exquisite watercolor art",
    "monsoonMemories": "atmospheric cinematic photograph of an old Indian street in Mumbai during a heavy monsoon downpour, roadside tea stall with tin roof glowing under warm lantern light, steaming cutting chai glasses, dark rain clouds overhead, wet bitumen road with puddles reflecting street lamps, black umbrellas, rain-soaked green trees, realistic water streams, authentic Indian monsoon mood, photorealistic"
}

for key, prompt in themes_prompts.items():
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1152&height=768&nologo=true&seed=42"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            print(f"SUCCESS {key}: fetched {len(data)} bytes ({resp.headers.get('Content-Type')})")
    except Exception as e:
        print(f"FAILED {key}: {str(e)}")
