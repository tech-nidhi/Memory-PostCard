import json
import os
import uuid
import base64
import logging
import urllib.request
import urllib.parse
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get('AWS_REGION', 'us-east-1')
BUCKET_NAME = os.environ.get('BUCKET_NAME', '')
RULE_NAME = "memory-postcard-daily-trigger"

bedrock_runtime = boto3.client('bedrock-runtime', region_name=REGION)
s3_client = boto3.client('s3', region_name=REGION)
events_client = boto3.client('events', region_name=REGION)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
    "Content-Type": "application/json"
}

# 10 IMMERSIVE REAL VISUAL SCENE THEMES
THEMES = {
    "snowyMorning": {
        "id": "snowyMorning",
        "name": "Snowy Morning",
        "mood": "Quiet & Serene",
        "style": "Winter Fine Art Photography",
        "environment": "A remote alpine wooden cabin surrounded by snow-covered pine trees in a mountain valley at dawn",
        "weather": "Gentle snowfall, frost-laden pine branches, cold air mist",
        "lighting": "Soft cold blue morning light with warm golden light glowing through cabin windows",
        "props": ["snow-covered wooden cabin", "fresh footprints in snow", "pine trees", "chimney smoke", "snowy rooftops"],
        "photo_url": "https://images.unsplash.com/photo-1517299321609-52687d1bc55a?w=1152&h=768&fit=crop&q=85&auto=format"
    },
    "rainyDay": {
        "id": "rainyDay",
        "name": "Rainy Day",
        "mood": "Reflective & Peaceful",
        "style": "Cinematic 35mm Street Photography",
        "environment": "A quiet old European city street during heavy evening rain outside a cozy café",
        "weather": "Active heavy rainfall, rain droplets on glass, puddles, mist",
        "lighting": "Overcast natural light mixed with warm yellow window lights and street lamp reflections on wet road",
        "props": ["dark umbrellas", "wet reflective pavement", "puddles", "steaming coffee cup", "rain coats"],
        "photo_url": "https://images.unsplash.com/photo-1519692933481-e162a57d6721?w=1152&h=768&fit=crop&q=85&auto=format"
    },
    "cityLights": {
        "id": "cityLights",
        "name": "City Lights",
        "mood": "Energetic & Electric",
        "style": "Nighttime Urban Street Photography",
        "environment": "A dense busy Tokyo street in Shibuya with illuminated Japanese storefronts and skyscrapers",
        "weather": "Nighttime urban mist, light rain reflections on asphalt",
        "lighting": "Vibrant cyan, magenta, and amber neon signs, glowing storefronts, traffic headlights",
        "props": ["yellow city taxis", "pedestrians crossing", "glowing neon signage", "wet road reflections"],
        "photo_url": "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?w=1152&h=768&fit=crop&q=85&auto=format"
    },
    "sunsetEscape": {
        "id": "sunsetEscape",
        "name": "Sunset Escape",
        "mood": "Nostalgic & Expansive",
        "style": "Golden Hour Travel Photography",
        "environment": "A quiet tropical beach at sunset with orange sun touching the horizon",
        "weather": "Clear warm evening sky with gold and pink illuminated clouds",
        "lighting": "Intense golden hour sunlight, long shadows, warm atmospheric haze",
        "props": ["silhouette of palm trees", "gentle waves reflecting sunset colors", "vintage van near shoreline"],
        "photo_url": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1152&h=768&fit=crop&q=85&auto=format"
    },
    "autumnPath": {
        "id": "autumnPath",
        "name": "Autumn Path",
        "mood": "Nostalgic & Warm",
        "style": "Rich Autumn Landscape Photography",
        "environment": "A narrow gravel forest path during peak autumn lined with tall maple trees",
        "weather": "Crisp autumn breeze, subtle distant forest mist",
        "lighting": "Warm late-afternoon amber sunlight filtering through orange and crimson canopy",
        "props": ["blanket of scarlet and golden fallen leaves covering ground", "rustic wooden fence", "old street lamp"],
        "photo_url": "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=1152&h=768&fit=crop&q=85&auto=format"
    },
    "mountainCalling": {
        "id": "mountainCalling",
        "name": "Mountain Calling",
        "mood": "Adventurous & Grand",
        "style": "High-Altitude Wilderness Photography",
        "environment": "Enormous alpine mountain peaks rising above a green valley and pine forest ridge",
        "weather": "Swirling mountain peak clouds, crisp thin air, dramatic sunbeams breaking through mist",
        "lighting": "Bright high-altitude sunlight contrasting sharp rocky ridges with deep shadow valleys",
        "props": ["narrow hiking trail on cliff edge", "lone hiker for scale", "distant mountain stream"],
        "photo_url": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1152&h=768&fit=crop&q=85&auto=format"
    },
    "cozyEvening": {
        "id": "cozyEvening",
        "name": "Cozy Evening",
        "mood": "Intimate & Peaceful",
        "style": "Warm Interior Fine Art Photography",
        "environment": "A cozy wooden cabin interior at night with an open book and tea mug on a table",
        "weather": "Rain visible through window glass, warm indoor sanctuary",
        "lighting": "Soft amber table lamp glow, flickering fireplace embers in background",
        "props": ["open hardcover book", "steaming ceramic mug of tea", "knitted blanket", "glowing candle"],
        "photo_url": "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=1152&h=768&fit=crop&q=85&auto=format"
    },
    "vintageVibes": {
        "id": "vintageVibes",
        "name": "Vintage Vibes",
        "mood": "Historical & Timeless",
        "style": "1950s 35mm Analog Film Photography",
        "environment": "A classic 1950s European railway station with mid-century architecture",
        "weather": "Soft analog film grain, subtle vintage sepia warmth",
        "lighting": "Soft golden vintage natural daylight, muted contrast characteristic of classic 35mm film",
        "props": ["vintage leather suitcase", "classic 1950s automobile", "analog clock tower", "historical clothing"],
        "photo_url": "https://images.unsplash.com/photo-1526772662000-3f88f10405ff?w=1152&h=768&fit=crop&q=85&auto=format"
    },
    "watercolorDream": {
        "id": "watercolorDream",
        "name": "Watercolor Dream",
        "mood": "Dreamy & Whimsical",
        "style": "Masterpiece Fine Art Watercolor Painting",
        "environment": "A dreamy wildflower meadow surrounding a serene lake and rolling hills at sunrise",
        "weather": "Soft misty air, delicate painterly clouds, gentle color washes",
        "lighting": "Luminous pastel daylight, soft watercolor pigment gradients",
        "props": ["blooming lavender and poppies", "gentle water ripples", "visible wet-on-wet watercolor washes"],
        "photo_url": "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=1152&h=768&fit=crop&q=85&auto=format"
    },
    "monsoonMemories": {
        "id": "monsoonMemories",
        "name": "Monsoon Memories",
        "mood": "Nostalgic & Evocative",
        "style": "Atmospheric Indian Monsoon Photography",
        "environment": "An Indian street in Mumbai during a heavy monsoon downpour beside a roadside chai stall",
        "weather": "Heavy monsoon downpour, dark dramatic rain clouds, water streaming off tin roof",
        "lighting": "Overcast stormy sky contrasted with warm yellow lantern glow from tea stall",
        "props": ["steaming cutting chai glasses", "black umbrellas", "glistening wet palm trees", "wet bitumen road"],
        "photo_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1152&h=768&fit=crop&q=85&auto=format"
    }
}

def clean_json_response(raw_text: str) -> dict:
    """Extract and parse JSON from model text output, stripping markdown code fences if present."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[:-3]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        text = text[start_idx:end_idx+1]
        
    return json.loads(text)

def get_s3_json(bucket: str, key: str, default=None):
    """Retrieve and parse JSON object from S3."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return json.loads(response['Body'].read().decode('utf-8'))
    except ClientError as e:
        if e.response['Error']['Code'] in ('NoSuchKey', '404'):
            return default
        logger.warning(f"Error reading S3 key {key}: {str(e)}")
        return default
    except Exception as e:
        logger.warning(f"Error reading S3 key {key}: {str(e)}")
        return default

def put_s3_json(bucket: str, key: str, data: dict):
    """Save JSON object to S3."""
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(data, indent=2).encode('utf-8'),
        ContentType='application/json'
    )

def normalize_postcard_item(item, bucket: str):
    """Ensure postcard item uses clean permanent S3 public URL and has valid fallbacks."""
    if not item or not isinstance(item, dict):
        return item
    item_copy = dict(item)
    img_key = item_copy.get('image_key')
    theme_id = item_copy.get('theme_id')
    
    if img_key and bucket:
        item_copy['image_url'] = f"https://{bucket}.s3.{REGION}.amazonaws.com/{img_key}"
    elif item_copy.get('image_url') and '?' in item_copy['image_url']:
        item_copy['image_url'] = item_copy['image_url'].split('?')[0]
    elif not item_copy.get('image_url') and theme_id in THEMES:
        item_copy['image_url'] = THEMES[theme_id]['photo_url']
        
    return item_copy

def fetch_real_theme_artwork(theme: dict, user_memory: str) -> tuple[bytes, str, str]:
    """Fetch high-resolution photographic scene artwork for the requested theme."""
    prompt = f"cinematic high-resolution photograph of {theme['environment']}, {theme['weather']}, {theme['lighting']}, {', '.join(theme['props'])}, {theme['style']}, 1152x768 photorealistic"
    
    # Primary: AI Image Generation Service (Pollinations / Sana AI Engine)
    ai_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1152&height=768&nologo=true&seed=42"
    req = urllib.request.Request(ai_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = resp.read()
            if len(data) > 10000:
                logger.info(f"Successfully generated AI image for theme {theme['name']} ({len(data)} bytes)")
                return data, "jpg", "image/jpeg"
    except Exception as e:
        logger.warning(f"AI image endpoint notice for theme {theme['name']}: {str(e)}. Using curated high-res scene photo.")

    # High-Resolution Photography Scene Fallback (Unsplash 1152x768 Real Scene)
    photo_url = theme.get("photo_url")
    req_photo = urllib.request.Request(photo_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req_photo, timeout=12) as resp:
        data = resp.read()
        logger.info(f"Successfully loaded real photographic scene for theme {theme['name']} ({len(data)} bytes)")
        return data, "jpg", "image/jpeg"

def select_autonomous_theme(history: list, requested_theme_key: str = "") -> dict:
    """Select a theme intelligently to guarantee high creative diversity across days."""
    if requested_theme_key in THEMES:
        return THEMES[requested_theme_key]

    recent_themes = [item.get('theme_id', '') for item in history[:4] if item.get('theme_id')]
    candidates = [t_key for t_key in THEMES if t_key not in recent_themes]
    if not candidates:
        candidates = list(THEMES.keys())

    selected_key = candidates[0]
    return THEMES[selected_key]

def run_autonomous_creative_agent(user_memory: str = "", requested_theme_key: str = "", override_location: str = "", override_time: str = "") -> dict:
    """Core Creative Agent logic that evaluates context, history, and invokes Bedrock to produce today's postcard."""
    bucket = BUCKET_NAME or os.environ.get('BUCKET_NAME', '')
    if not bucket:
        raise ValueError("BUCKET_NAME environment variable is not configured.")

    # 1. Fetch history & select theme
    history = get_s3_json(bucket, "postcards/history.json", default=[])
    theme = select_autonomous_theme(history, requested_theme_key)

    # 2. Context evaluation
    now = datetime.utcnow()
    formatted_date = now.strftime("%d %b %Y")
    day_name = now.strftime("%A")
    month_name = now.strftime("%B")

    # Prompt Bedrock Nova Lite for poem & caption
    prompt = f"""You are Memory Postcard's autonomous creative AI agent.
Today's Date: {formatted_date} ({day_name})
Season/Month: {month_name}
Selected Visual Theme: {theme['name']} ({theme['environment']})
User Context/Memory: {user_memory or 'An autonomous reflection on quiet moments and journeys'}

Write the poetic text for today's postcard matching this visual theme.
Return ONLY a strict JSON object with NO extra text outside JSON:
{{
  "title": "A short evocative title in ALL CAPS matching {theme['name']}, under 6 words",
  "poem": "3 to 5 short poetic lines capturing the mood of {theme['name']}, separated by \\n",
  "quote": "A poignant quote under 15 words matching this theme",
  "location": "{override_location or 'Somewhere Peaceful'}",
  "time": "{override_time or formatted_date}",
  "creative_reasoning": "A 1-2 sentence explanation of why this theme was chosen based on history and context."
}}"""

    body = {
        "messages": [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ],
        "inferenceConfig": {
            "temperature": 0.75,
            "maxTokens": 1000
        }
    }

    try:
        response = bedrock_runtime.invoke_model(
            modelId="amazon.nova-lite-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body)
        )
        response_body = json.loads(response['body'].read().decode('utf-8'))
        raw_text = response_body['output']['message']['content'][0]['text']
        text_data = clean_json_response(raw_text)
    except Exception as e:
        logger.warning(f"Bedrock Nova Lite notice: {str(e)}. Using creative text fallback.")
        text_data = {
            "title": f"{theme['name'].upper()} REFLECTION",
            "poem": f"Quiet moments in {theme['name'].lower()}\nMoments frozen in time\nA gentle warmth remains.",
            "quote": "Every postcard tells a story of another world.",
            "location": override_location or "Somewhere Peaceful",
            "time": override_time or formatted_date,
            "creative_reasoning": f"Explored {theme['name']} theme to bring visual storytelling and environment variety."
        }

    title = text_data.get('title', f"{theme['name'].upper()} MEMORY").upper()
    poem = text_data.get('poem', 'Golden sunlight on quiet streets\nMoments frozen in time\nA gentle warmth remains.')
    quote = text_data.get('quote', 'Every memory is a postcard from the heart.')
    location = text_data.get('location', override_location or 'Somewhere Peaceful')
    time_period = text_data.get('time', override_time or formatted_date)
    reasoning = text_data.get('creative_reasoning', f"Selected {theme['name']} theme for immersive environment storytelling.")

    # 3. Generate REAL scene artwork (NO vector SVG gradients/circles)
    image_bytes, ext, content_type = fetch_real_theme_artwork(theme, user_memory)

    # 4. Save real scene image to S3 under postcards/YYYY/MM/DD/postcard_{id}.jpg
    postcard_id = str(uuid.uuid4())
    s3_key_image = f"postcards/{now.strftime('%Y/%m/%d')}/postcard_{postcard_id}.{ext}"
    
    s3_client.put_object(
        Bucket=bucket,
        Key=s3_key_image,
        Body=image_bytes,
        ContentType=content_type
    )

    clean_image_url = f"https://{bucket}.s3.{REGION}.amazonaws.com/{s3_key_image}"

    # 5. Build full postcard record
    postcard_record = {
        "id": postcard_id,
        "title": title,
        "poem": poem,
        "quote": quote,
        "theme_id": theme['id'],
        "theme": theme['name'],
        "mood": theme['mood'],
        "style": theme['style'],
        "location": location,
        "time": time_period,
        "image_url": clean_image_url,
        "image_key": s3_key_image,
        "generated_at": formatted_date,
        "generated_timestamp": now.isoformat(),
        "created_automatically": True,
        "created_label": f"Created automatically this morning ({now.strftime('%I:%M %p')})",
        "creative_reasoning": reasoning,
        "streak_count": len(history) + 1
    }

    put_s3_json(bucket, "postcards/latest.json", postcard_record)

    history.insert(0, postcard_record)
    put_s3_json(bucket, "postcards/history.json", history[:30])

    logger.info(f"AUTONOMOUS_EXECUTION_COMPLETE: Postcard {postcard_id} created successfully with REAL scene artwork for '{theme['name']}'. Key: {s3_key_image}")
    return postcard_record

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    http_method = event.get('requestContext', {}).get('http', {}).get('method', '') or event.get('httpMethod', '')
    if http_method == 'OPTIONS':
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({"message": "CORS preflight OK"})
        }

    if event.get('source') == 'aws.events' or event.get('detail-type') == 'Scheduled Event':
        logger.info("EventBridge Autonomous Scheduler Triggered!")
        record = run_autonomous_creative_agent()
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "message": "Autonomous daily postcard generated successfully",
                "postcard": record
            })
        }

    try:
        path = event.get('rawPath', '') or event.get('path', '')
        raw_body = event.get('body', '{}')
        if event.get('isBase64Encoded', False):
            raw_body = base64.b64decode(raw_body).decode('utf-8')
            
        data = json.loads(raw_body) if isinstance(raw_body, str) else (raw_body or {})
        action = data.get('action', '') or event.get('queryStringParameters', {}).get('action', '')

        bucket = BUCKET_NAME or os.environ.get('BUCKET_NAME', '')

        # Action: Return List of Available Themes
        if action == 'themes':
            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps({"themes": list(THEMES.values())})
            }

        # Action: User Schedule Update
        if action == 'schedule' or action == 'set_schedule':
            hour_utc = int(data.get('hour_utc', 8))
            schedule_time = data.get('schedule_time', f"{hour_utc:02d}:00 AM")
            cron_expr = f"cron(0 {hour_utc} * * ? *)"

            try:
                events_client.put_rule(
                    Name=RULE_NAME,
                    ScheduleExpression=cron_expr,
                    State='ENABLED',
                    Description=f"Daily autonomous trigger for Memory Postcard at {schedule_time} UTC"
                )
            except Exception as ev_err:
                logger.warning(f"Could not update EventBridge rule dynamically: {str(ev_err)}")

            schedule_info = {
                "schedule_time": schedule_time,
                "hour_utc": hour_utc,
                "cron_expression": cron_expr,
                "updated_at": datetime.utcnow().strftime("%d %b %Y %H:%M UTC")
            }
            put_s3_json(bucket, "postcards/schedule.json", schedule_info)

            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps({
                    "message": f"Daily schedule updated to {schedule_time}!",
                    "schedule": schedule_info
                })
            }

        # Action: Get Schedule
        if action == 'get_schedule':
            schedule_info = get_s3_json(bucket, "postcards/schedule.json", default={
                "schedule_time": "08:00 AM",
                "hour_utc": 8,
                "cron_expression": "cron(0 8 * * ? *)"
            })
            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps(schedule_info)
            }

        # Action: Get Latest Postcard
        if action == 'latest' or path.endswith('/latest') or (http_method == 'GET' and not action):
            latest = get_s3_json(bucket, "postcards/latest.json")
            if not latest:
                latest = run_autonomous_creative_agent()
            latest = normalize_postcard_item(latest, bucket)
            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps(latest)
            }

        # Action: Get History
        if action == 'history' or path.endswith('/history'):
            history = get_s3_json(bucket, "postcards/history.json", default=[])
            if not history:
                latest = get_s3_json(bucket, "postcards/latest.json")
                if latest:
                    history = [latest]
            normalized_history = [normalize_postcard_item(item, bucket) for item in history]
            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps({"history": normalized_history})
            }

        # Action: Trigger Generation (With Theme Selection)
        memory = data.get('memory', '').strip()
        theme_key = data.get('theme', '').strip()
        location = data.get('location', '')
        time_period = data.get('time', '')

        record = run_autonomous_creative_agent(
            user_memory=memory,
            requested_theme_key=theme_key,
            override_location=location,
            override_time=time_period
        )

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps(record)
        }
        
    except Exception as e:
        logger.exception("Error processing postcard request")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": str(e)})
        }
