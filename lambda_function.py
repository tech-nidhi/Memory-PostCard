import json
import os
import uuid
import base64
import logging
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

# 10 STRUCTURED IMMERSIVE VISUAL THEMES
THEMES = {
    "rainyDay": {
        "id": "rainyDay",
        "name": "Rainy Day",
        "mood": "Reflective & Peaceful",
        "style": "Cinematic 35mm Photography",
        "environment": "A quiet old European or Indian city street outside a vintage café with warm glowing windows",
        "weather": "Active heavy rainfall, mist, water droplets glistening on surfaces, wet cobblestones",
        "lighting": "Overcast natural daylight mixed with warm yellow window lights and street lamp reflections on wet pavement",
        "props": ["dark umbrella", "steaming coffee cup on window ledge", "puddles with sky reflections", "rain-streaked glass"],
        "composition": "Eye-level 35mm street view, deep atmospheric perspective, cinematic wet reflections",
        "palette": ("#2B3A4A", "#4A6B82", "#1C2530", "#0D131A")
    },
    "snowyMorning": {
        "id": "snowyMorning",
        "name": "Snowy Morning",
        "mood": "Quiet & Serene",
        "style": "Winter Fine Art Photography",
        "environment": "A snow-covered timber cabin in a quiet mountain pine forest village",
        "weather": "Gently falling snow, frost-laden pine branches, visible cold air mist, crisp winter atmosphere",
        "lighting": "Pale soft winter morning sunlight casting gentle golden rays over cold blue snow drifts",
        "props": ["snow-capped wooden rooftops", "smoke rising softly from chimney", "deep footprints in fresh snow", "warm golden window light"],
        "composition": "Wide landscape composition framing the cabin among towering pine trees, high crisp detail",
        "palette": ("#E0F2FE", "#7DD3FC", "#1E293B", "#0F172A")
    },
    "sunsetEscape": {
        "id": "sunsetEscape",
        "name": "Sunset Escape",
        "mood": "Nostalgic & Expansive",
        "style": "Golden Hour Landscape Photography",
        "environment": "A dramatic coastal cliff viewpoint overlooking a tranquil ocean bay or desert highway",
        "weather": "Clear warm evening sky with thin wispy clouds illuminated in radiant pink and gold",
        "lighting": "Low sun near the horizon, intense golden hour glare, long dramatic shadows, radiant sunset glow",
        "props": ["silhouette of coastal rocks or palm trees", "glistening ocean surface", "winding coastal path"],
        "composition": "Cinematic wide-angle view, sun positioned near lower third horizon, dramatic scale",
        "palette": ("#FDE68A", "#F97316", "#7C2D12", "#451A03")
    },
    "autumnPath": {
        "id": "autumnPath",
        "name": "Autumn Path",
        "mood": "Nostalgic & Warm",
        "style": "Rich Autumn Landscape Photography",
        "environment": "A winding gravel trail through an old forest park lined with ancient maple trees",
        "weather": "Crisp autumn breeze, falling golden leaves drifting in the air, soft distant forest mist",
        "lighting": "Warm late-afternoon amber sunlight filtering through orange and scarlet leaves",
        "props": ["blanket of crimson and golden fallen leaves covering ground", "rustic wooden fence", "old iron street lamp"],
        "composition": "Leading lines following the winding path into the glowing forest canopy",
        "palette": ("#FED7AA", "#EA580C", "#7C2D12", "#361102")
    },
    "mountainCalling": {
        "id": "mountainCalling",
        "name": "Mountain Calling",
        "mood": "Adventurous & Grand",
        "style": "High-Altitude Wilderness Photography",
        "environment": "Majestic alpine mountain peaks towering above a green valley and pine forest ridge",
        "weather": "Swirling mountain peak clouds, crisp thin air, dramatic sunbeams breaking through mist",
        "lighting": "Bright high-altitude sunlight contrasting sharp rocky ridges with deep shadow valleys",
        "props": ["narrow hiking trail on cliff edge", "distant mountain stream", "tiny human figure for epic scale"],
        "composition": "Low-angle grand wilderness landscape, vertical mountain majesty, deep atmospheric depth",
        "palette": ("#BAE6FD", "#0284C7", "#0C4A6E", "#032030")
    },
    "cozyEvening": {
        "id": "cozyEvening",
        "name": "Cozy Evening",
        "mood": "Intimate & Peaceful",
        "style": "Warm Interior Fine Art Photography",
        "environment": "A warm rustic reading corner inside a timber cabin beside a rain-beaded window",
        "weather": "Quiet evening rain visible through window glass, warm indoor sanctuary",
        "lighting": "Soft amber glow from a vintage desk lamp and flickering fireplace embers",
        "props": ["stack of old hardcover books", "steaming ceramic mug of tea", "chunky knit wool blanket", "glowing candle"],
        "composition": "Medium close-up still life framing the cozy nook, shallow depth of field, warm rich bokeh",
        "palette": ("#FEF3C7", "#D97706", "#78350F", "#451A03")
    },
    "vintageVibes": {
        "id": "vintageVibes",
        "name": "Vintage Vibes",
        "mood": "Historical & Timeless",
        "style": "Authentic 1950s 35mm Analog Film",
        "environment": "A classic 1950s train platform or European cobble town square",
        "weather": "Clear soft retro afternoon air, fine analog film grain, subtle vintage sepia warmth",
        "lighting": "Soft golden vintage natural daylight, muted contrast characteristic of classic film",
        "props": ["vintage leather suitcase", "classic 1950s automobile in background", "old analog clock tower", "iron benches"],
        "composition": "Classic documentary-style 35mm framing, rich organic texture, nostalgic timeless depth",
        "palette": ("#FDE8CD", "#B45309", "#582C0E", "#2D1505")
    },
    "cityLights": {
        "id": "cityLights",
        "name": "City Lights",
        "mood": "Energetic & Electric",
        "style": "Nighttime Urban Street Photography",
        "environment": "A bustling downtown avenue flanked by towering skyscrapers and illuminated storefronts",
        "weather": "Nighttime mist after rain, wet asphalt reflecting bright city lights",
        "lighting": "Vibrant cyan, magenta, and amber neon signs, glowing shop windows, passing car headlights",
        "props": ["yellow city taxis", "pedestrians holding umbrellas", "glowing street signs", "wet road reflections"],
        "composition": "Dynamic urban perspective looking down a glowing avenue, rich color contrast",
        "palette": ("#DDD6FE", "#7C3AED", "#2E1065", "#0F051D")
    },
    "watercolorDream": {
        "id": "watercolorDream",
        "name": "Watercolor Dream",
        "mood": "Dreamy & Whimsical",
        "style": "Masterful Fine Art Watercolor Painting",
        "environment": "A dreamy wildflower meadow surrounding a serene lake and distant rolling hills",
        "weather": "Soft misty air, delicate painterly clouds, gentle color washes across the sky",
        "lighting": "Soft luminous pastel daylight, gentle watercolor pigment gradients",
        "props": ["blooming lavender and poppies", "gentle water ripples", "soft painted cottage in distance"],
        "composition": "Painterly impressionistic landscape with visible cold-press paper texture and soft bleeds",
        "palette": ("#F472B6", "#A855F7", "#4C1D95", "#1E0638")
    },
    "monsoonMemories": {
        "id": "monsoonMemories",
        "name": "Monsoon Memories",
        "mood": "Nostalgic & Evocative",
        "style": "Atmospheric Indian Monsoon Photography",
        "environment": "An Indian neighborhood street beside a roadside chai stall under a tin roof",
        "weather": "Heavy monsoon downpour, dark dramatic rain clouds, water streaming off tin roof",
        "lighting": "Overcast stormy monsoon sky contrasted with warm yellow lantern glow from tea stall",
        "props": ["cutting chai glasses", "black umbrellas", "glistening wet palm trees", "rainwater puddles"],
        "composition": "Atmospheric street scene framing the warm chai stall against rain-soaked greenery",
        "palette": ("#99F6E4", "#0D9488", "#115E59", "#042F2C")
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

def create_theme_svg_bytes(theme_key: str, memory: str, location: str) -> tuple[bytes, str]:
    """Generate high-quality vector artwork tailored to the specific visual theme."""
    theme = THEMES.get(theme_key, THEMES["rainyDay"])
    c1, c2, c3, c4 = theme["palette"]
    title_text = theme["name"].upper()
    loc_clean = (location or "POSTCARD").upper()

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1152" height="768" viewBox="0 0 1152 768">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="{c2}"/>
    </linearGradient>
    <linearGradient id="overlayGrad" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{c3}" stop-opacity="0.88"/>
      <stop offset="100%" stop-color="{c4}" stop-opacity="0.95"/>
    </linearGradient>
  </defs>
  <rect width="1152" height="768" fill="url(#bgGrad)"/>
  <circle cx="576" cy="300" r="240" fill="{c2}" opacity="0.35"/>
  <path d="M0 460 Q288 380 576 460 T1152 460 L1152 768 L0 768 Z" fill="url(#overlayGrad)"/>
  <path d="M0 550 Q384 470 768 550 T1152 550 L1152 768 L0 768 Z" fill="{c4}"/>
  <text x="576" y="690" font-family="Georgia, serif" font-size="26" font-weight="bold" fill="#FFFDF9" text-anchor="middle" letter-spacing="6" opacity="0.85">{title_text} · {loc_clean}</text>
</svg>"""
    return svg_content.encode('utf-8'), "image/svg+xml"

def build_rich_image_prompt(theme: dict, user_memory: str) -> str:
    """Build an explicit 13-point detailed visual prompt for Bedrock Nova Canvas."""
    props_str = ", ".join(theme['props'])
    return f"""High-resolution {theme['style']} of {theme['environment']}.
Atmosphere & Weather: {theme['weather']}.
Lighting: {theme['lighting']}.
Visual elements & details: {props_str}.
Composition: {theme['composition']}.
Context: Inspired by memory '{user_memory or theme['name']}'.
Camera & Optics: 35mm lens, atmospheric depth, sharp environmental details, realistic texture.
DO NOT render any text, letters, words, titles, labels, or watermarks inside the generated artwork."""

def generate_illustration(theme: dict, user_memory: str, location: str) -> tuple[bytes, str, str]:
    """Call Amazon Nova Canvas with rich environment prompt or fallback to vector theme artwork."""
    image_prompt = build_rich_image_prompt(theme, user_memory)
    logger.info(f"Generating image prompt for theme '{theme['name']}': {image_prompt}")

    body = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {
            "text": image_prompt
        },
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "height": 768,
            "width": 1152,
            "cfgScale": 8.5
        }
    }

    try:
        response = bedrock_runtime.invoke_model(
            modelId="amazon.nova-canvas-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body)
        )
        response_body = json.loads(response['body'].read().decode('utf-8'))
        base64_image = response_body['images'][0]
        return base64.b64decode(base64_image), "png", "image/png"
    except Exception as e:
        logger.warning(f"Bedrock Nova Canvas notice: {str(e)}. Generating custom theme vector artwork.")
        svg_bytes, content_type = create_theme_svg_bytes(theme['id'], user_memory, location)
        return svg_bytes, "svg", content_type

def select_autonomous_theme(history: list, requested_theme_key: str = "") -> dict:
    """Select a theme intelligently to guarantee high creative diversity across days."""
    if requested_theme_key in THEMES:
        return THEMES[requested_theme_key]

    recent_themes = [item.get('theme_id', '') for item in history[:4] if item.get('theme_id')]
    
    # Filter candidates to avoid recent repetitions
    candidates = [t_key for t_key in THEMES if t_key not in recent_themes]
    if not candidates:
        candidates = list(THEMES.keys())

    # Cycle deterministically or select first candidate
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
        logger.warning(f"Bedrock Nova Lite notice: {str(e)}. Using creative fallback.")
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

    # 3. Generate artwork
    image_bytes, ext, content_type = generate_illustration(theme, user_memory, location)

    # 4. Save artwork to S3
    postcard_id = str(uuid.uuid4())
    s3_key_image = f"postcards/{now.strftime('%Y/%m/%d')}/postcard_{postcard_id}.{ext}"
    
    s3_client.put_object(
        Bucket=bucket,
        Key=s3_key_image,
        Body=image_bytes,
        ContentType=content_type
    )

    presigned_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': s3_key_image},
        ExpiresIn=604800
    )

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
        "image_url": presigned_url,
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

    logger.info(f"AUTONOMOUS_EXECUTION_COMPLETE: Postcard {postcard_id} created successfully with theme '{theme['name']}'.")
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
            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps({"history": history})
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
