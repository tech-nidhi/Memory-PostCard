# 💌 Memory Postcard: Always-On Creative AI Agent

> An always-on creative AI agent built on AWS that autonomously creates a new illustrated digital postcard every morning — *a postcard you didn't have to make.*

![AWS Builder Center Challenge](https://main.d3upkw4ewckj1x.amplifyapp.com)

---

## 🌟 Product Concept & Challenge Goal

**Memory Postcard** transforms your digital experience into a personal creative mailbox. Every day, the system autonomously creates a new postcard based on the day's context (date, day of week, season), creative themes, recent history evaluation, and Bedrock AI generation. 

When the user opens the application, today's postcard is already waiting for them with a badge:
> **Created automatically this morning at 8:00 AM**

This project satisfies the **AWS Builder Center Challenge ("Set Your Creative App Free")** by implementing a genuine autonomous, scheduled creative agent loop on AWS.

---

## 🌐 Live AWS Production Endpoints

| Service | Component | Live Production URL / Target |
| :--- | :--- | :--- |
| **AWS Amplify Hosting** | Frontend SPA | [**https://main.d3upkw4ewckj1x.amplifyapp.com**](https://main.d3upkw4ewckj1x.amplifyapp.com) |
| **AWS API Gateway** | HTTP API Endpoint | `https://0674b4zip9.execute-api.us-east-1.amazonaws.com/` |
| **AWS EventBridge** | Daily Cron Scheduler | `memory-postcard-daily-trigger` (`cron(0 8 * * ? *)`) |
| **AWS Lambda** | Creative Agent Handler | `memory-postcard-backend` (Python 3.12, `us-east-1`) |
| **Amazon Bedrock** | Generative AI Models | `amazon.nova-lite-v1:0` & `amazon.nova-canvas-v1:0` |
| **Amazon S3** | Postcard Artwork & History | `memory-postcard-storage-110836100897` |

---

## 🏗️ Architecture Diagram

```
                       AUTOMATED DAILY SCHEDULER
                                 │
                     Amazon EventBridge Scheduler
                        (cron: 08:00 AM UTC daily)
                                 │
                                 ▼
 USER                    AWS Lambda Handler
  │                (memory-postcard-backend)
  │                              │
  │                      Context & History
  ▼                      Evaluation Engine
AWS Amplify                      │
  │                  ┌───────────┴───────────┐
  │                  ▼                       ▼
  │          Amazon Bedrock           Amazon Bedrock
  │         (Nova Lite Text)       (Nova Canvas Image)
  │                  │                       │
  │                  └───────────┬───────────┘
  │                              ▼
  │                     Amazon S3 Bucket
  │                (postcards/YYYY/MM/DD/...)
  │                              │
  └──────────────────────────────┴───────────────► Today's Postcard & History Gallery
```

---

## 🧠 Autonomous Creative Agent Decision Engine

Unlike basic LLM wrappers that generate random outputs, **Memory Postcard** enforces a structured decision pipeline:

1. **Context Evaluation**: Analyzes today's date (`YYYY-MM-DD`), day of week (e.g. *Friday*), month, and season.
2. **Creative History Inspection**: Reads recent postcards stored in S3 (`postcards/history.json`) to inspect recent visual styles (`Vintage`, `Film`, `Watercolor`, `Illustrated`, `Minimal`) and themes.
3. **Variety & Non-Repetition**: Selects a visual style that avoids repeating recent choices (e.g., if recent postcards used *Vintage*, the agent prefers *Watercolor* or *Illustrated*).
4. **Bedrock AI Generation**: Invokes Amazon Bedrock Nova Lite to formulate:
   - Creative reasoning
   - Title (<6 words in ALL CAPS)
   - 3-5 line poem & quote
   - Detailed image generation prompt (excluding embedded text)
5. **Artwork Render & S3 Presigned URL**: Renders artwork using Bedrock Nova Canvas (or SVG fallback), uploads to S3, updates `latest.json` & `history.json`, and logs CloudWatch metrics.

---

## 📊 Autonomous Execution Evidence & Verification

To verify that generation occurred autonomously without user interaction:

### 1. CloudWatch Log Verification
Open **AWS CloudWatch Logs** -> Log Group `/aws/lambda/memory-postcard-backend`:

Look for log entries emitted by EventBridge trigger executions:
```text
EventBridge Autonomous Scheduler Triggered!
AUTONOMOUS_EXECUTION_COMPLETE: Postcard de474c4d-b7c3-43ac-baa6-68f0f8e4ef48 created successfully (A SERENE SUMMER MORNING). S3 Key: postcards/2026/08/21/postcard_de474c4d.svg
```

### 2. Manual CLI Simulation Trigger (Dev Mode)
To simulate the daily EventBridge trigger instantly during development:
```bash
aws lambda invoke \
  --function-name memory-postcard-backend \
  --payload '{"source":"aws.events"}' \
  response.json

cat response.json
```

---

## 🛠️ Local Development & Testing

### Prerequisites
- Node.js & Python 3.12
- AWS CLI configured for `us-east-1`

### Running the App Locally
1. Clone the repository:
   ```bash
   git clone https://github.com/tech-nidhi/Memory-PostCard.git
   cd Memory-PostCard
   ```
2. Serve the static application:
   ```bash
   python3 -m http.server 8080
   ```
3. Open `http://localhost:8080` in your web browser.

---

## 🔑 Environment Variables & Security

Backend environment configuration in AWS Lambda:
- `AWS_REGION`: `us-east-1`
- `BUCKET_NAME`: `memory-postcard-storage-110836100897`

*No secret keys, IAM credentials, or Bedrock tokens are exposed to the browser. The frontend communicates exclusively with the AWS API Gateway endpoint.*
