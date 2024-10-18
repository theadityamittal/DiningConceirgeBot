import json
import boto3
import logging
import os
import requests
import random
from utils import *

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def lambda_handler(event, context):
    """
    Lambda function to process messages from the SQS queue and send personalized
    restaurant suggestions to the users.

    Args:
        event (dict): The Lambda event containing the message records.
        context (object): The context of the Lambda function.

    Returns:
        dict: A dictionary containing the response code and body.
    """
    logger.info("Scheduled Event from AWS EventBridge")

    # Check if the event contains records
    if 'Records' not in event:
        logger.info("Queue Empty...")
        return {
            'statusCode': 200,
            'body': json.dumps('Nothing to process in queue...')
        }

    # Iterate through the messages in the event
    for record in event['Records']:
        message_body = json.loads(record['body'])
        receipt_handle = record['receiptHandle']

        logger.info(f"Processing message: {message_body}")
        
        cuisine = message_body['Cuisine']
        host = os.getenv('ES_HOST')
        url = f"{host}/_search"
        query = {
            "query": {
                "match": {
                    "Cuisine": {
                        "query": cuisine.capitalize(),
                        "operator": "and"
                    }
                }
            },
            "size": 1000
        }
        headers = {"Content-Type": "application/json"}

        # Make the Elasticsearch request
        es_response = requests.get(
            url, headers=headers, data=json.dumps(query),
            auth=(os.getenv('ES_USERNAME'), os.getenv('ES_PASSWORD'))
        )
        
        logger.info(f"Elasticsearch response: {es_response}")

        restaurant_data = es_response.json()
        logger.info(f"Elasticsearch response body: {json.dumps(restaurant_data)}")
        
        if restaurant_data['hits']['total']['value'] > 0:
            data_list = restaurant_data['hits']['hits']
            random_list = [hit['_id'] for hit in data_list]

            # Select 5 random restaurants
            selected_restaurants = random.sample(random_list, k=5)
            
            logger.info(f"Selected Restaurants: {selected_restaurants}")

            # Fetch full restaurant details from DynamoDB
            dynamodb = boto3.resource('dynamodb')
            restaurants_list = dynamodb.batch_get_item(
                RequestItems={
                    'yelp-restaurants': {'Keys': [{'business_id': id} for id in selected_restaurants]}
                }
            )

            logger.info(f"Fetched restaurant details: {restaurants_list}")

            # Send restaurant suggestions via SES
            ses_send_mail(restaurants_list, message_body)

            # Update past suggestions in DynamoDB
            create_or_update_users_past_suggestions(
                restaurants_list['Responses']['yelp-restaurants'], message_body
            )

        else:
            logger.info(f"No restaurants found for cuisine: {cuisine}")

        # Delete the message from the SQS queue
        sqs_delete_message(receipt_handle)

    return {
        'statusCode': 200,
        'body': json.dumps('Lambda executed successfully!')
    }

def sqs_delete_message(receipt_handle):
    """
    Deletes the processed message from the SQS queue.

    This function takes the Receipt Handle of the message to be deleted
    and deletes it from the SQS queue.

    :param receipt_handle: The Receipt Handle of the message to be deleted
    :type receipt_handle: str
    """
    sqs = boto3.client('sqs')
    queue_url = os.getenv('QUEUE_URL')
    logger.info(f"Deleting message with receipt handle: {receipt_handle} from queue: {queue_url}")

    try:
        response = sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
        logger.info(f"Deleted SQS message: {response}")

    except sqs.exceptions.QueueDoesNotExist as e:
        logger.error(f"The specified queue does not exist: {str(e)}")
        raise

    except Exception as e:
        logger.error(f"Error deleting message: {str(e)}")
        raise


def ses_send_mail(restaurants_list, dining_details):
    """
    Sends an email with restaurant suggestions using Amazon SES.

    Args:
        restaurants_list (dict): A dictionary containing restaurant details fetched from DynamoDB.
        dining_details (dict): A dictionary containing the user's dining preferences and email.
    """
    SENDER = os.getenv('SENDER_EMAIL')
    RECIPIENT = dining_details['Email']
    SUBJECT = "Restaurant Suggestions from Foody"
    
    columns = ['name', 'address', 'rating', 'reviews']
    reordered_dicts = [
        reorder_dict(restaurant, columns)
        for restaurant in restaurants_list['Responses']['yelp-restaurants']
    ]

    # Convert the reordered restaurant details into an HTML table
    BODY_HTML = dict_to_html_table(reordered_dicts, dining_details['Cuisine'], dining_details['Location'])

    ses_client = boto3.client('ses')

    try:
        # Send email using the SES client
        response = ses_client.send_email(
            Destination={'ToAddresses': [RECIPIENT]},
            Message={
                'Body': {'Html': {'Charset': 'UTF-8', 'Data': BODY_HTML}},
                'Subject': {'Charset': 'UTF-8', 'Data': SUBJECT},
            },
            Source=SENDER,
        )
        logger.info(f"Email sent! Message ID: {response['MessageId']}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

def create_or_update_users_past_suggestions(restaurants, dining_details):
    """
    Updates the user's past restaurant suggestions in DynamoDB.

    Args:
        restaurants: List of restaurant details to be updated.
        dining_details: User's dining preferences and details.
    """
    logger.info(f"Attempting to update past suggestions for {dining_details} with {restaurants}")
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('past-restaurant-suggestions')
        
        record = {
            'user_id': dining_details['user_id'],
            'dining_details': dining_details,
            'restaurants': restaurants
        }
        
        # Update the item in DynamoDB
        response = table.put_item(Item=record)
        logger.info(f"Updated past suggestions: {response}")
    except Exception as e:
        logger.error(f"Failed to update past suggestions: {e}")
