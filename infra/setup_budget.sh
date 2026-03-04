#!/bin/bash
# AWS Budget Email Notification Setup
# Creates an email notification for 'MyBudgetShield' budget at 80% actual spend threshold

set -e

BUDGET_NAME="MyBudgetShield"
EMAIL="surya24.bandari@gmail.com"
ACCOUNT_ID="809880865943"
THRESHOLD=80

echo "Setting up AWS Budget notification for: $BUDGET_NAME"
echo "Email: $EMAIL"
echo "Threshold: ${THRESHOLD}% of actual spend"
echo ""

# Create SNS topic for budget alerts (if it doesn't exist)
TOPIC_ARN=$(aws sns create-topic \
    --name budget-alerts-${BUDGET_NAME} \
    --output text \
    --query 'TopicArn')

echo "✅ SNS Topic: $TOPIC_ARN"

# Subscribe email to SNS topic
aws sns subscribe \
    --topic-arn "$TOPIC_ARN" \
    --protocol email \
    --notification-endpoint "$EMAIL"

echo "✅ Email subscription created (check $EMAIL for confirmation)"
echo ""

# Create budget notification
# Note: This assumes the budget 'MyBudgetShield' already exists
# If not, you need to create the budget first using aws budgets create-budget

aws budgets create-notification \
    --account-id "$ACCOUNT_ID" \
    --budget-name "$BUDGET_NAME" \
    --notification NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=${THRESHOLD},ThresholdType=PERCENTAGE \
    --subscribers SubscriptionType=SNS,Address="$TOPIC_ARN"

echo "✅ Budget notification created successfully!"
echo ""
echo "Summary:"
echo "  - Budget: $BUDGET_NAME"
echo "  - Alert at: ${THRESHOLD}% of actual spend"
echo "  - Notification: $EMAIL (via SNS)"
echo ""
echo "⚠️  IMPORTANT: Check your email and confirm the SNS subscription!"
