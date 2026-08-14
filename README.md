# 💌 Memory Postcard

> Turn your written memories into AI-generated illustrated postcards powered by Amazon Bedrock Nova models on AWS.

![Memory Postcard](https://main.d3upkw4ewckj1x.amplifyapp.com)

## 🌐 Live Demos & AWS Deployment

- **Live Web Application (AWS Amplify Hosting)**: [https://main.d3upkw4ewckj1x.amplifyapp.com](https://main.d3upkw4ewckj1x.amplifyapp.com)
- **Live Backend API (AWS API Gateway + Lambda)**: `https://0674b4zip9.execute-api.us-east-1.amazonaws.com/`

---

## 🛠️ Tech Stack

- **Frontend**: Single-page vanilla HTML5 / CSS3 / JavaScript app (no build step, ready for static hosting or AWS Amplify).
- **Backend**: AWS Lambda (Python 3.12) exposed via AWS API Gateway HTTP API.
- **AI Models**: Amazon Bedrock — `amazon.nova-lite-v1:0` for structured text generation & `amazon.nova-canvas-v1:0` for image generation.
- **Storage**: Amazon S3 bucket for postcard images with 7-day presigned GET URLs.

---

## 📁 Repository Structure

- `index.html` — Frontend UI with cream vintage design, memory form, postcard stub canvas export, local gallery, and responsive layout.
- `lambda_function.py` — Python 3.12 AWS Lambda handler for Bedrock text/image generation and S3 presigned URL creation.
- `deploy.sh` — Automated deployment script using AWS CLI (`us-east-1`).
- `.gitignore` — Ignore temporary zip files and cache.

---

## 🚀 How to Run Locally

1. Clone this repository:
   ```bash
   git clone <YOUR_GITHUB_REPO_URL>
   cd "Weekend Challenge"
   ```
2. Serve `index.html` using any local HTTP server:
   ```bash
   python3 -m http.server 8080
   ```
3. Open `http://localhost:8080` in your web browser.

---

## ⚡ Deployment to AWS

To deploy your own backend and frontend to AWS:

```bash
export AWS_ACCESS_KEY_ID="<YOUR_KEY>"
export AWS_SECRET_ACCESS_KEY="<YOUR_SECRET>"
export AWS_DEFAULT_REGION="us-east-1"

./deploy.sh
```
