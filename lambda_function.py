import json
import os
import uuid
import base64
import logging
import urllib.parse
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
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        text = text[start_idx:end_idx+1]
        
    return json.loads(text)

def generate_text_content(memory: str, mood: str, style: str, location: str, time_period: str) -> dict:
    """Call Amazon Nova Lite (amazon.nova-lite-v1:0) to generate title, poem, quote, and image prompt."""
    prompt = f"""You are an artist creating a memory postcard.
User Memory Details:
- Memory description: {memory}
- Mood/Feeling: {mood or 'Nostalgic'}
- Postcard visual style: {style or 'Vintage'}
- Location: {location or 'Unknown'}
- Time period: {time_period or 'Sometime in memory'}

Return ONLY a strict JSON object with NO extra text outside JSON. Format:
{{
  "title": "A short, evocative postcard title in ALL CAPS, under 6 words",
  "poem": "3 to 5 short poetic lines capturing the mood, separated by \\n newline characters",
  "quote": "A poignant quote under 15 words about this memory",
  "image_prompt": "A detailed visual description for an artistic illustration representing this memory in {style} style. DO NOT include any text, letters, words, or signs inside the image itself. Focus on scenery, lighting, colors, objects, atmosphere, and artistic composition suitable for a 1152x768 postcard image."
}}"""

    body = {
        "messages": [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ],
        "inferenceConfig": {
            "temperature": 0.7,
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
        return clean_json_response(raw_text)
    except Exception as e:
        logger.warning(f"Bedrock Nova Lite notice: {str(e)}. Using smart text synthesis fallback.")
        words = memory.strip().split()
        title = ( " ".join(words[:4]) if words else "MEMORY POSTCARD" ).upper()
        return {
            "title": title,
            "poem": f"Golden light upon the shore\nA quiet moment to remember\nWarmth that stays forevermore.",
            "quote": "Every memory is a postcard from the heart.",
            "image_prompt": f"A beautiful {style} illustration of {memory}"
        }

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

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    # CORS Preflight
    http_method = event.get('requestContext', {}).get('http', {}).get('method', '') or event.get('httpMethod', '')
    if http_method == 'OPTIONS':
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({"message": "CORS preflight OK"})
        }

    try:
        raw_body = event.get('body', '{}')
        if event.get('isBase64Encoded', False):
            raw_body = base64.b64decode(raw_body).decode('utf-8')
            
        data = json.loads(raw_body) if isinstance(raw_body, str) else (raw_body or {})
        
        memory = data.get('memory', '').strip()
        if not memory:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "Memory text is required."})
            }
            
        mood = data.get('mood', 'Nostalgic')
        style = data.get('style', 'Vintage')
        location = data.get('location', '') or 'Somewhere Special'
        time_period = data.get('time', '') or 'Once Upon a Time'
        
        # 1. Call Nova Lite for text
        text_data = generate_text_content(memory, mood, style, location, time_period)
        
        title = text_data.get('title', 'SUMMER MEMORIES').upper()
        poem = text_data.get('poem', 'Golden sunlight on quiet streets\nMoments frozen in time\nA gentle warmth remains.')
        quote = text_data.get('quote', 'Every memory is a postcard from the heart.')
        image_prompt = text_data.get('image_prompt', f'A beautiful {style} postcard artwork of {memory}')
        
        # 2. Call Nova Canvas (or SVG fallback)
        image_bytes, ext, content_type = generate_illustration(image_prompt, memory, style, location)
        
        # 3. Upload to S3 & generate 7-day presigned URL
        bucket = BUCKET_NAME or os.environ.get('BUCKET_NAME', '')
        if not bucket:
            raise ValueError("BUCKET_NAME environment variable is not configured.")
            
        file_key = f"postcards/{uuid.uuid4()}.{ext}"
        s3_client.put_object(
            Bucket=bucket,
            Key=file_key,
            Body=image_bytes,
            ContentType=content_type
        )
        
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': file_key},
            ExpiresIn=604800
        )
        
        # 4. Return successful response
        generated_at = datetime.utcnow().strftime("%d %b %Y")
        
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "title": title,
                "poem": poem,
                "quote": quote,
                "location": location,
                "time": time_period,
                "image_url": presigned_url,
                "generated_at": generated_at
            })
        }
        
    except Exception as e:
        logger.exception("Error processing postcard request")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": str(e)})
        }
