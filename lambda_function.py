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

bedrock_runtime = boto3.client('bedrock-runtime', region_name=REGION)
s3_client = boto3.client('s3', region_name=REGION)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
    "Content-Type": "application/json"
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

def create_fallback_svg_bytes(memory: str, style: str, location: str) -> tuple[bytes, str]:
    """Generate custom stylized SVG vector artwork bytes and content type."""
    palettes = {
        "Vintage": ("#FCEABB", "#C1652F", "#4A3728", "#2C1E16"),
        "Film": ("#3A6073", "#3A7BD5", "#1A2634", "#0F172A"),
        "Watercolor": ("#E0C3FC", "#8EC5FC", "#4A0E4E", "#2B062F"),
        "Illustrated": ("#FFD194", "#D1913C", "#6A3805", "#3B1E02"),
        "Minimal": ("#E2E8F0", "#94A3B8", "#334155", "#0F172A")
    }
    c1, c2, c3, c4 = palettes.get(style, palettes["Vintage"])
    loc_clean = (location or "MEMORY").upper()

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1152" height="768" viewBox="0 0 1152 768">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="{c2}"/>
    </linearGradient>
    <linearGradient id="overlayGrad" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{c3}" stop-opacity="0.85"/>
      <stop offset="100%" stop-color="{c4}" stop-opacity="0.95"/>
    </linearGradient>
  </defs>
  <rect width="1152" height="768" fill="url(#bgGrad)"/>
  <circle cx="576" cy="320" r="230" fill="{c2}" opacity="0.4"/>
  <path d="M0 480 Q288 400 576 480 T1152 480 L1152 768 L0 768 Z" fill="url(#overlayGrad)"/>
  <path d="M0 560 Q384 480 768 560 T1152 560 L1152 768 L0 768 Z" fill="{c4}"/>
  <text x="576" y="690" font-family="Georgia, serif" font-size="24" fill="#FFFDF9" text-anchor="middle" letter-spacing="4" opacity="0.7">{style.upper()} POSTCARD · {loc_clean}</text>
</svg>"""
    return svg_content.encode('utf-8'), "image/svg+xml"

def generate_illustration(image_prompt: str, memory: str, style: str, location: str) -> tuple[bytes, str, str]:
    """Call Amazon Nova Canvas or generate vector artwork, returning (image_bytes, extension, content_type)."""
    body = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {
            "text": image_prompt
        },
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "height": 768,
            "width": 1152,
            "cfgScale": 8.0
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
        logger.warning(f"Bedrock Nova Canvas notice: {str(e)}. Generating custom vector artwork.")
        svg_bytes, content_type = create_fallback_svg_bytes(memory, style, location)
        return svg_bytes, "svg", content_type

def run_autonomous_creative_agent(user_memory: str = "", override_style: str = "", override_mood: str = "", override_location: str = "", override_time: str = "") -> dict:
    """Core Creative Agent logic that evaluates context, history, and invokes Bedrock to produce today's postcard."""
    bucket = BUCKET_NAME or os.environ.get('BUCKET_NAME', '')
    if not bucket:
        raise ValueError("BUCKET_NAME environment variable is not configured.")

    # 1. Fetch recent creative history from S3
    history = get_s3_json(bucket, "postcards/history.json", default=[])
    recent_styles = [item.get('style', '') for item in history[:3] if item.get('style')]
    recent_themes = [item.get('theme', '') for item in history[:3] if item.get('theme')]

    # 2. Context evaluation
    now = datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")
    formatted_date = now.strftime("%d %b %Y")
    day_name = now.strftime("%A")
    month_name = now.strftime("%B")

    # Select style to avoid repetition if not specified
    available_styles = ["Vintage", "Film", "Watercolor", "Illustrated", "Minimal"]
    candidate_styles = [s for s in available_styles if s not in recent_styles[:2]]
    selected_style = override_style or (candidate_styles[0] if candidate_styles else "Watercolor")

    # Prompt Bedrock Nova Lite
    prompt = f"""You are Memory Postcard's autonomous creative AI agent.
Today's Date: {formatted_date} ({day_name})
Season/Month: {month_name}
User Memory Context: {user_memory or 'An autonomous morning reflection on seasons, quiet journeys, and peaceful moments'}
Recent Visual Styles Used: {', '.join(recent_styles) if recent_styles else 'None'}
Selected Target Style: {selected_style}

Create a brand new illustrated postcard.
Return ONLY a strict JSON object with NO extra text outside JSON:
{{
  "title": "A short, evocative postcard title in ALL CAPS, under 6 words",
  "poem": "3 to 5 short poetic lines capturing the mood, separated by \\n newline characters",
  "quote": "A poignant quote under 15 words",
  "theme": "A creative theme, e.g. Monsoon Nostalgia, Early Morning Light, Station Solitude",
  "mood": "{override_mood or 'Reflective'}",
  "style": "{selected_style}",
  "location": "{override_location or 'Somewhere Peaceful'}",
  "time": "{override_time or formatted_date}",
  "image_prompt": "A detailed visual description for an artistic illustration representing this theme in {selected_style} style. DO NOT include text, letters, words, or signs inside the image.",
  "creative_reasoning": "A 1-2 sentence explanation of why you chose this theme and visual style based on history and today's context."
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
        logger.info(f"Nova Lite raw output: {raw_text}")
        text_data = clean_json_response(raw_text)
    except Exception as e:
        logger.warning(f"Bedrock Nova Lite notice: {str(e)}. Using creative fallback.")
        text_data = {
            "title": f"MORNING IN {day_name.upper()}",
            "poem": "Golden sunlight on quiet streets\nMoments frozen in time\nA gentle warmth remains.",
            "quote": "Every morning brings a new postcard from the world.",
            "theme": "Morning Reflection",
            "mood": override_mood or "Reflective",
            "style": selected_style,
            "location": override_location or "Somewhere Peaceful",
            "time": override_time or formatted_date,
            "image_prompt": f"A serene {selected_style} illustration of early morning sunlight",
            "creative_reasoning": f"Explored {selected_style} style to provide visual variety following recent history."
        }

    title = text_data.get('title', 'MORNING REFLECTION').upper()
    poem = text_data.get('poem', 'Golden sunlight on quiet streets\nMoments frozen in time\nA gentle warmth remains.')
    quote = text_data.get('quote', 'Every memory is a postcard from the heart.')
    theme = text_data.get('theme', 'Quiet Journey')
    mood = text_data.get('mood', 'Reflective')
    style = text_data.get('style', selected_style)
    location = text_data.get('location', override_location or 'Somewhere Peaceful')
    time_period = text_data.get('time', override_time or formatted_date)
    image_prompt = text_data.get('image_prompt', f'A beautiful {style} illustration')
    reasoning = text_data.get('creative_reasoning', 'Autonomous creation based on daily context.')

    # 3. Generate artwork
    image_bytes, ext, content_type = generate_illustration(image_prompt, user_memory or theme, style, location)

    # 4. Save artwork to S3 under postcards/YYYY/MM/DD/postcard_{id}.{ext}
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

    # 5. Build postcard record
    postcard_record = {
        "id": postcard_id,
        "title": title,
        "poem": poem,
        "quote": quote,
        "theme": theme,
        "mood": mood,
        "style": style,
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

    # 6. Save latest.json and update history.json in S3
    put_s3_json(bucket, "postcards/latest.json", postcard_record)

    history.insert(0, postcard_record)
    put_s3_json(bucket, "postcards/history.json", history[:30])

    logger.info(f"AUTONOMOUS_EXECUTION_COMPLETE: Postcard {postcard_id} created successfully ({title}). S3 Key: {s3_key_image}")
    return postcard_record

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Handle CORS Preflight
    http_method = event.get('requestContext', {}).get('http', {}).get('method', '') or event.get('httpMethod', '')
    if http_method == 'OPTIONS':
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({"message": "CORS preflight OK"})
        }

    # Handle EventBridge Scheduled Event
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

        # Action 1: Get Latest Postcard (or auto-generate if missing)
        if action == 'latest' or path.endswith('/latest') or (http_method == 'GET' and not action):
            latest = get_s3_json(bucket, "postcards/latest.json")
            if not latest:
                logger.info("No latest postcard found in S3. Triggering initial autonomous generation.")
                latest = run_autonomous_creative_agent()
            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps(latest)
            }

        # Action 2: Get History
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

        # Action 3: Trigger Generation (Development Test or Manual Form Submission)
        memory = data.get('memory', '').strip()
        mood = data.get('mood', '')
        style = data.get('style', '')
        location = data.get('location', '')
        time_period = data.get('time', '')

        record = run_autonomous_creative_agent(
            user_memory=memory,
            override_style=style,
            override_mood=mood,
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
