import json
import logging
import boto3
import os

logger = logging.getLogger()
logger.setLevel("INFO")

def lambda_handler(event, context):

    logger.info(f"Event {event}")
    message = event['messages'][0]

    logger.info(f"Context {context}")

    # Lex API call
    lex = boto3.client('lexv2-runtime')
    
    response = lex.recognize_text(
        botId=os.environ.get('BOT_ID'), 
        botAliasId=os.environ.get('BOT_ALIAS_ID'),
        sessionId= '908027408981943',
        localeId='en_US',  
        text=message['unstructured']['text']
    )
    
    logger.info(response)

    messages = []
    for message in response['messages']:
        if message['contentType'] != 'PlainText':
            messages.append({ 'type' : 'structured', 'structured' : { 'text': message['content']}})

        else:
            messages.append({ 'type' : 'unstructured', 'unstructured' : { 'text': message['content']}})
    
    return {
        'statusCode': 200,
        'messages': messages
    }