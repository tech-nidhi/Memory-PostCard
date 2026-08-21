#!/usr/bin/env bash
set -e

# Memory Postcard AWS Deployment Script
# Region: us-east-1

REGION="us-east-1"
FUNCTION_NAME="memory-postcard-backend"
ROLE_NAME="memory-postcard-lambda-role"
POLICY_NAME="memory-postcard-lambda-policy"
RULE_NAME="memory-postcard-daily-trigger"

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
        
    echo "Waiting for Lambda code update to complete..."
    aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION"
        
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

FUNCTION_ARN=$(aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" --query "Configuration.FunctionArn" --output text)

# 6. Configure EventBridge Daily Scheduler (Every morning at 08:00 AM UTC)
echo "Configuring EventBridge Daily Scheduler ($RULE_NAME)..."
aws events put-rule \
    --name "$RULE_NAME" \
    --schedule-expression "cron(0 8 * * ? *)" \
    --state "ENABLED" \
    --description "Daily autonomous trigger for Memory Postcard creative agent at 8:00 AM UTC" \
    --region "$REGION" > /dev/null

aws lambda add-permission \
    --function-name "$FUNCTION_NAME" \
    --statement-id EventBridgeDailyTrigger \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:$REGION:$AWS_ACCOUNT_ID:rule/$RULE_NAME" \
    --region "$REGION" 2>/dev/null || true

aws events put-targets \
    --rule "$RULE_NAME" \
    --targets "Id"="1","Arn"="$FUNCTION_ARN" \
    --region "$REGION" > /dev/null

# 7. Configure API Gateway HTTP API Integration
echo "Configuring API Gateway HTTP API..."
API_ID=$(aws apigatewayv2 get-apis --region "$REGION" --query "Items[?Name=='memory-postcard-api'].ApiId | [0]" --output text 2>/dev/null || true)

if [ -z "$API_ID" ] || [ "$API_ID" == "None" ]; then
    API_ID=$(aws apigatewayv2 create-api \
        --name "memory-postcard-api" \
        --protocol-type HTTP \
        --cors-configuration '{"AllowOrigins":["*"],"AllowMethods":["*"],"AllowHeaders":["*"]}' \
        --region "$REGION" \
        --query "ApiId" \
        --output text)
        
    INTEGRATION_ID=$(aws apigatewayv2 create-integration \
        --api-id "$API_ID" \
        --integration-type AWS_PROXY \
        --integration-uri "$FUNCTION_ARN" \
        --payload-format-version "2.0" \
        --region "$REGION" \
        --query "IntegrationId" \
        --output text)

    aws apigatewayv2 create-route --api-id "$API_ID" --route-key "POST /" --target "integrations/$INTEGRATION_ID" --region "$REGION" > /dev/null
    aws apigatewayv2 create-route --api-id "$API_ID" --route-key "GET /" --target "integrations/$INTEGRATION_ID" --region "$REGION" > /dev/null
    aws apigatewayv2 create-route --api-id "$API_ID" --route-key "OPTIONS /" --target "integrations/$INTEGRATION_ID" --region "$REGION" > /dev/null
    aws apigatewayv2 create-stage --api-id "$API_ID" --stage-name '$default' --auto-deploy --region "$REGION" > /dev/null

    aws lambda add-permission \
        --function-name "$FUNCTION_NAME" \
        --statement-id APIGatewayInvokeAccess \
        --action lambda:InvokeFunction \
        --principal apigateway.amazonaws.com \
        --source-arn "arn:aws:execute-api:$REGION:$AWS_ACCOUNT_ID:$API_ID/*/*" \
        --region "$REGION" 2>/dev/null || true
fi

API_ENDPOINT="https://$API_ID.execute-api.$REGION.amazonaws.com/"

echo "=================================================="
echo " Deployment Complete!"
echo " S3 Bucket: $BUCKET_NAME"
echo " Lambda Function: $FUNCTION_NAME"
echo " EventBridge Rule: $RULE_NAME (cron(0 8 * * ? *))"
echo " Live API Endpoint: $API_ENDPOINT"
echo "=================================================="
echo ""
echo "Next step: Ensure index.html has:"
echo "const API_URL = \"$API_ENDPOINT\";"
