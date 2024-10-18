# **Dining Concierge System with AWS Lambda, Lex, and SQS**

## **Overview**

This project implements a **Dining Concierge System** leveraging AWS services such as **Lambda, Lex V2, DynamoDB, SQS, SES, EventBridge Scheduler, and Elasticsearch**. The system provides personalized restaurant recommendations based on user preferences and automates requests through Lambda functions and an SQS queue.

---

## **Architecture**

The system consists of multiple Lambda functions (LF0, LF1, and LF2) with specific roles:

1. **LF0 (ChatHandler):**  
   - Handles user messages from an API client or chatbot.  
   - Sends messages to Lex for intent recognition and processes the response.

2. **LF1 (Dining Suggestion Orchestrator):**  
   - Validates user inputs and sends requests to SQS.  
   - Checks for past suggestions in DynamoDB and emails suggestions if found.  
   - Sends new suggestions to the queue if not available in history.

3. **LF2 (Queue Worker):**  
   - Polls SQS messages and queries Elasticsearch for restaurant details.  
   - Sends personalized restaurant recommendations via SES and updates DynamoDB.

4. **EventBridge Scheduler:**  
   - Automates LF2 invocation every minute to ensure timely request processing.

---

## **Technologies Used**

- **AWS Lambda:** Serverless backend logic for request processing.
- **Amazon Lex V2:** Conversational AI chatbot to detect user intents.
- **Amazon SQS:** Queue service to manage dining requests.
- **Amazon SES:** Email service to send personalized restaurant recommendations.
- **Amazon DynamoDB:** NoSQL database to store past suggestions.
- **Amazon Elasticsearch:** Fast restaurant search based on cuisine and location.
- **EventBridge Scheduler:** Automates Lambda invocation for queue processing.

---

## **Setup and Deployment Instructions**

### **Prerequisites**
- AWS Account
- Node.js or Python environment (for local development)
- AWS CLI installed and configured

### **Steps to Deploy**

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/your-username/dining-concierge-system.git
   cd dining-concierge-system
   ```

2. **Set Up AWS Resources:**
   - Create **Lex V2 Bot** with required intents (e.g., `DiningSuggestionsIntent`).
   - Create **DynamoDB Table:**  
     - Table name: `past-restaurant-suggestions`  
     - Primary key: `user_id`
   - Set up **SQS Queue** and **SES Email Verification**.

3. **Deploy Lambda Functions:**
   - Package and deploy LF0, LF1, and LF2 using the AWS CLI or AWS Console.
     ```bash
     zip function.zip lambda_function.py
     aws lambda update-function-code --function-name LF0-ChatHandler --zip-file fileb://function.zip
     # Repeat for LF1 and LF2
     ```

4. **Set Up Environment Variables:**  
   In each Lambda function, configure the following environment variables:
   - **LF0:**
     - `BOT_ID`: Lex Bot ID  
     - `BOT_ALIAS_ID`: Lex Bot Alias ID  
   - **LF1 and LF2:**
     - `SENDER_EMAIL`: SES verified sender email  
     - `QUEUE_URL`: SQS Queue URL  
     - `ES_HOST`: Elasticsearch endpoint URL  
     - `ES_USERNAME`: Elasticsearch username  
     - `ES_PASSWORD`: Elasticsearch password  

5. **Configure EventBridge Scheduler:**
   - Set up an **EventBridge rule** to trigger LF2 every minute:
     ```bash
     aws events put-rule --schedule-expression "rate(1 minute)" --name LF2Scheduler
     aws lambda add-permission --function-name LF2-QueueWorker --statement-id EventBridgeInvoke --action lambda:InvokeFunction --principal events.amazonaws.com --source-arn arn:aws:events:us-east-1:123456789012:rule/LF2Scheduler
     aws events put-targets --rule LF2Scheduler --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:123456789012:function:LF2-QueueWorker"
     ```

---

## **Troubleshooting**

1. **S3 Bucket Not Accessible:**
   - Check bucket policies and IAM roles for correct permissions.

2. **Lex Integration Errors:**
   - Ensure Lambda function permissions are correctly configured with Lex.

3. **Lambda Timeouts:**
   - Adjust the Lambda timeout settings if tasks exceed the default duration.

4. **SES Email Not Sent:**
   - Verify the sender and recipient email addresses are SES-verified.

---

## **Team Members**

| Name              | NYU NetID                    |
|-------------------|------------------------------|
| Aditya Mittal     | am13294                      |
| Affan Khamse      | ak10529                      |

---

## **License**

This project is licensed under the MIT License. See the `LICENSE` file for more details.
