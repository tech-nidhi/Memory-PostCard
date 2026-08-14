#!/usr/bin/env bash
set -e

# Memory Postcard AWS Deployment Script
# Region: us-east-1

REGION="us-east-1"
FUNCTION_NAME="memory-postcard-backend"
ROLE_NAME="memory-postcard-lambda-role"
POLICY_NAME="memory-postcard-lambda-policy"

echo "=================================================="
echo " Starting Deployment for Memory Postcard Backend"
echo " Region: $REGION"
echo "=================================================="

# Check AWS CLI installation
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed. Please install and configure it first."
    exit 1
fi

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || true)
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "Error: Unable to retrieve AWS Account ID. Make sure your AWS CLI credentials are configured."
    exit 1
fi

BUCKET_NAME="memory-postcard-storage-${AWS_ACCOUNT_ID}"
echo "Using S3 Bucket Name: $BUCKET_NAME"

# 1. Create S3 Bucket
echo "Creating S3 bucket $BUCKET_NAME in $REGION..."
if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
    echo "S3 Bucket $BUCKET_NAME already exists."
else
    aws s3api create-bucket \
        --bucket "$BUCKET_NAME" \
        --region "$REGION"
    echo "S3 Bucket created successfully."
fi

# Enable CORS on S3 Bucket
echo "Configuring CORS on S3 bucket..."
cat <<EOF > /tmp/s3_cors.json
{
  "CORSRules": [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedOrigins": ["*"],
      "MaxAgeSeconds": 3000
    }
  ]
}
EOF
aws s3api put-bucket-cors --bucket "$BUCKET_NAME" --cors-configuration file:///tmp/s3_cors.json

# 2. Create IAM Role for Lambda
echo "Creating IAM Role $ROLE_NAME..."
cat <<EOF > /tmp/lambda_trust_policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query "Role.Arn" --output text 2>/dev/null || true)

if [ -z "$ROLE_ARN" ]; then
    ROLE_ARN=$(aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file:///tmp/lambda_trust_policy.json \
        --query "Role.Arn" \
        --output text)
    echo "Role created: $ROLE_ARN"
    echo "Waiting 10 seconds for IAM role propagation..."
    sleep 10
else
    echo "Role $ROLE_NAME already exists: $ROLE_ARN"
fi

# 3. Attach IAM Policy (Bedrock, S3, CloudWatch Logs)
echo "Attaching policy to IAM Role..."
cat <<EOF > /tmp/lambda_policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
EOF

aws iam put-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name "$POLICY_NAME" \
    --policy-document file:///tmp/lambda_policy.json

# 4. Zip Lambda Function
echo "Zipping lambda_function.py..."
rm -f lambda.zip
zip -q lambda.zip lambda_function.py

# 5. Create or Update Lambda Function
echo "Deploying Lambda Function $FUNCTION_NAME..."
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" >/dev/null 2>&1; then
    echo "Updating existing Lambda function code..."
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file fileb://lambda.zip \
        --region "$REGION" > /dev/null
        
    echo "Updating function configuration..."
    aws lambda update-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --runtime "python3.12" \
        --handler "lambda_function.lambda_handler" \
        --timeout 60 \
        --memory-size 512 \
        --environment "Variables={BUCKET_NAME=$BUCKET_NAME}" \
        --region "$REGION" > /dev/null
else
    echo "Creating new Lambda function..."
    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --runtime "python3.12" \
        --role "$ROLE_ARN" \
        --handler "lambda_function.lambda_handler" \
        --zip-file fileb://lambda.zip \
        --timeout 60 \
        --memory-size 512 \
        --environment "Variables={BUCKET_NAME=$BUCKET_NAME}" \
        --region "$REGION" > /dev/null
fi

# 6. Create Lambda Function URL with public auth NONE and CORS
echo "Configuring Lambda Function URL..."
FUNCTION_URL=$(aws lambda get-function-url-config --function-name "$FUNCTION_NAME" --region "$REGION" --query "FunctionUrl" --output text 2>/dev/null || true)

if [ -z "$FUNCTION_URL" ]; then
    FUNCTION_URL=$(aws lambda create-function-url-config \
        --function-name "$FUNCTION_NAME" \
        --auth-type NONE \
        --cors '{"AllowOrigins":["*"],"AllowMethods":["*"],"AllowHeaders":["*"]}' \
        --region "$REGION" \
        --query "FunctionUrl" \
        --output text)
else
    aws lambda update-function-url-config \
        --function-name "$FUNCTION_NAME" \
        --auth-type NONE \
        --cors '{"AllowOrigins":["*"],"AllowMethods":["POST","OPTIONS"],"AllowHeaders":["*"]}' \
        --region "$REGION" > /dev/null
fi

# 7. Grant public permission to Function URL
echo "Setting public access permissions..."
aws lambda add-permission \
    --function-name "$FUNCTION_NAME" \
    --statement-id FunctionURLAllowPublicAccess \
    --action lambda:InvokeFunctionUrl \
    --principal "*" \
    --function-url-auth-type NONE \
    --region "$REGION" 2>/dev/null || true

echo "=================================================="
echo " Deployment Complete!"
echo " S3 Bucket: $BUCKET_NAME"
echo " Lambda Function: $FUNCTION_NAME"
echo " Public Function URL: $FUNCTION_URL"
echo "=================================================="
echo ""
echo "Next step: Copy the Public Function URL above into index.html near the top of the <script> tag:"
echo "const API_URL = \"$FUNCTION_URL\";"
echo "Then deploy index.html to AWS Amplify Hosting!"
