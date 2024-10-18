import json
import datetime
import os
import dateutil.parser
import logging
from utils import *
import boto3
import time


import re
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def ses_send_mail(restaurants_list, dining_details):
    """Sends an email with restaurant suggestions using Amazon SES.
    
    Args:
        restaurants_list: A list of restaurant dictionaries.
        dining_details: A dictionary containing user's dining preferences and email.
    """
    SENDER = os.environ['SENDER_EMAIL']
    RECIPIENT = dining_details['Email']
    SUBJECT = "Restaurant Suggestions from Foody"
    CHARSET = "UTF-8"
    
    columns = ['name', 'address', 'rating', 'reviews']
    logger.debug(f"Restaurants list: {restaurants_list}")

    reordered_dicts = [reorder_dict(restaurant, columns) for restaurant in restaurants_list]

    # Convert restaurant information to HTML table
    BODY_HTML = dict_to_html_table(reordered_dicts, dining_details['Cuisine'], dining_details['Location'])

    client = boto3.client('ses')
    
    try:
        response = client.send_email(
            Destination={'ToAddresses': [RECIPIENT]},
            Message={
                'Body': {'Html': {'Charset': CHARSET, 'Data': BODY_HTML}},
                'Subject': {'Charset': CHARSET, 'Data': SUBJECT},
            },
            Source=SENDER,
        )
        logger.info(f"Email sent! Message ID: {response['MessageId']}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

def sqs_send(dining_details):
    """
    Sends the user's dining details to the SQS queue.

    Args:
        dining_details (dict): A dictionary containing the user's dining preferences.

    Returns:
        bool: True if the message is sent successfully, otherwise False.
    """

    try:
        sqs = boto3.client('sqs')
        
        # Send the message to the queue
        result = sqs.send_message(
            QueueUrl=os.environ.get('QUEUE_URL'),
            MessageBody=json.dumps(dining_details)
        )

        logger.info(f"SQS response: {result}")

        return True

    except Exception as err:
        logger.error(err)
        
        return False

# Function to check if email is valid
def isvalid_email(email):
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))

# Function to check if location is valid
def isvalid_location(location):
    logger.info(f"location: {location}")
    valid_cities = ['manhattan']
    print(location.lower() in valid_cities)
    return location.lower() in valid_cities

# Function to check if Cuisine Type is valid
def isvalid_cuisine_type(cuisine_type):
    logger.info(cuisine_type)
    cuisine_types = ['thai', 'indian', 'french', 'italian', 'mexican', 'chinese', 'japanese']
    return cuisine_type.lower() in cuisine_types

# Function to check if date is valid
def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False

# Function to check if time is valid
def isvalid_time(time):
    try:
        dateutil.parser.parse(time)
        return True
    except ValueError:
        return False

# Function to build validation result
def build_validation_result(isvalid, violated_slot, message_content):
    return {
        'validationResult': {
            'isValid': isvalid,
            'violatedSlot': violated_slot,
            'message': {'content': message_content, 'contentType': 'PlainText'}
        }
    }


def validate_dining(slots):
    """
    This function validates the slots provided by the user for making a restaurant reservation.
    
    Parameters:
    slots (dict): A dictionary containing the slot values provided by the user.
    
    Returns:
    dict: A dictionary containing a boolean indicating whether the slots are valid and the slot values.
    """

    location = try_ex(lambda: slots['Location']['value']['interpretedValue'])
    d_time = try_ex(lambda: slots['DiningTime']['value']['interpretedValue'])
    d_date =  try_ex(lambda: slots['DiningDate']['value']['interpretedValue'])
    n_people = safe_int(try_ex(lambda: slots['NumberOfPeople']['value']['interpretedValue']))
    cuisine = try_ex(lambda: slots['Cuisine']['value']['interpretedValue'])
    email = try_ex(lambda: slots['Email']['value']['interpretedValue'])

    logger.info(f"{location}, {d_time}, {n_people}, {d_date}, {cuisine}, {email}")

    if location and not isvalid_location(location):
        return build_validation_result(False, 'Location', f"We currently do not support {location} as a valid destination. Manhattan is the hottest spot we serve. Could please enter your preferred location?")

    if d_date:
        if not isvalid_date(d_date):
            return build_validation_result(False, 'DiningDate', 'I did not understand your date.  When would you like to make reservation?')
        logger.info(datetime.datetime.strptime(d_date, '%Y-%m-%d').date())
        
        logger.info(f"Todays date: {datetime.date.today()}")
        if datetime.datetime.strptime(d_date, '%Y-%m-%d').date() <=  datetime.date.today():
            return build_validation_result(False, 'DiningDate', 'Reservations must be scheduled at least one day in advance. Can you try a different date?')

    if d_time:
        if not isvalid_time(d_time):
            return build_validation_result(False, 'DiningTime', 'I did not get your time.  When would you like to make reservation?')

    if n_people is not None and (n_people < 1 or n_people > 100):
        return build_validation_result(False, 'NumberOfPeople', 'You can make a reservation for from 1 to 100 person. How many number of people would you like to make reservation for?')

    if cuisine and not isvalid_cuisine_type(cuisine):
        return build_validation_result(False, 'Cuisine', 'Cuisine Type seems to be inaccurate. Would you like to try  cuisine from Thai, Indian, French, Italian, Mexican, Chinese or Japanese?')

    if email and not isvalid_email(email):
        return build_validation_result(False, 'Email', 'Provided Email is inaccurate. Please check the email and try again.')

    return {'validationResult': {'isValid': True}}
    
def dining_suggestion(intent_request):
    """
    This function handles the DiningSuggestionsIntent and is responsible for validating the slot values and 
    passing the request to the SQS queue.
    
    Parameters:
    intent_request (dict): The intent request of the user.
    
    Returns:
    dict: A dictionary containing the response to be sent to the user.
    """
    
    intent_name = intent_request['sessionState']['intent']['name']
    
    #get the slot values
    location = try_ex(lambda: intent_request['sessionState']['intent']['slots']['Location']['value']['interpretedValue'])
    d_time = try_ex(lambda: intent_request['sessionState']['intent']['slots']['DiningTime']['value']['interpretedValue'])
    d_date = try_ex(lambda: intent_request['sessionState']['intent']['slots']['DiningDate']['value']['interpretedValue'])
    n_people = safe_int(try_ex(lambda: intent_request['sessionState']['intent']['slots']['NumberOfPeople']['value']['interpretedValue']))
    cuisine = try_ex(lambda: intent_request['sessionState']['intent']['slots']['Cuisine']['value']['interpretedValue'])
    email = try_ex(lambda: intent_request['sessionState']['intent']['slots']['Email']['value']['interpretedValue'])
    
    session_attributes = intent_request['sessionState'].get('sessionAttributes', {})

    reservation = {
        'ReservationType': 'Dining',
        'Location': location,
        'Cuisine': cuisine,
        'DiningTime': d_time,
        'DiningDate': d_date,
        'NumberOfPeople': n_people,
        'Email': email
    }

    # check the invocation source
    if intent_request['invocationSource']=="DialogCodeHook":
        
        #validate the slots
        validation_result = validate_dining(intent_request['sessionState']['intent']['slots'])
        logger.info(validation_result)
        
        # ask again for the correct value if there is any invalid slots
        if not validation_result['validationResult']['isValid']:
            return elicit_slot(intent_request['sessionState'], validation_result['validationResult']['violatedSlot'], validation_result['validationResult']['message'])

        else:
            # Pass directly to Lex
            return delegate(intent_request['sessionState'])

    elif intent_request['invocationSource'] == 'FulfillmentCodeHook':

        reservation['user_id'] = intent_request['sessionId']
        result = sqs_send(reservation)
        logger.debug(f"SQS result: {result}")
       
        message = {
           "contentType": "PlainText",
            "content": "You’re all set. Expect my suggestions shortly! Have a good day."
        }
        if result:
            return close(intent_name,  message)

        else:
            message['content'] = "Sorry, we are facing some issues!"
            return close(intent_name,  message)

    message = {'contentType': 'PlainText', 'content': 'You’re all set. Expect my suggestions shortly! Have a good day.'}
    return close(intent_name,  message)


def greeting_intent(intent_request):
    """
    This function handles the GreetingIntent.
    It first checks if the user has any previous suggestions saved in DynamoDB.
    If the user has previous suggestions, it asks the user if they want to receive the suggestions via email.
    """
    intent_name = intent_request['sessionState']['intent']['name']
    logger.info("In GreetingIntent")
    
    # Check if user has past suggestions in dynamo db
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('past-restaurant-suggestions')
    
    restaurants_list = table.get_item(Key={'user_id': '908027408981943'}) 
    
    logger.info(f"restaurants_list: {restaurants_list}")
    
    if intent_request['interpretations'][0]['intent']['confirmationState']=='Confirmed':
        logger.info(f"sessionAttributes: {intent_request['sessionState']['sessionAttributes']}")
        
        data = json.loads(intent_request['sessionState']['sessionAttributes']['restaurants_list'])
        
        logger.info(f"Load restaurants: {data}")
        
        # Send email with restaurant suggestions
        ses_send_mail(data['restaurants'] , data['dining_details'])
        message = {
            'content': "Great! You will receive suggestions on your email shortly!", 
            'contentType': 'PlainText'
        }
        
        # Clear out session attributes
        intent_request['sessionState']['sessionAttributes'] = {}
        return close(intent_name,  message)
    
    elif intent_request['interpretations'][0]['intent']['confirmationState']=='Denied':
        message = {
            'content': "No problem! Tell me how can I assist you today?", 
            'contentType': 'PlainText'
        }
        
        # Clear out session attributes
        intent_request['sessionState']['sessionAttributes'] = {}
        return close(intent_name,  message)

    if 'Item' in restaurants_list:
        logger.debug(restaurants_list)
        cuisine_type = restaurants_list['Item']['dining_details']['Cuisine']
        location = restaurants_list['Item']['dining_details']['Location']
        message = {
            'content': f"You previously requested suggestions for {cuisine_type} in {location}, do you want it over the email now?", 
            'contentType': 'PlainText'
        }
        
        # Save the user's previous suggestions in session attributes
        intent_request['sessionState']['sessionAttributes'].update({'restaurants_list': json.dumps(restaurants_list['Item'], default=decimal_default)})
        # Pass the confirmIntent
        return confirm_intent(intent_request['sessionState'], message)
    
    return close(intent_name,  closing_message)
    
def thankyou_intent(intent_name):
    message = {
    "contentType": "PlainText",
    "content": "You’re welcome! Have a nice day.",
    
    }
    
    
    return close(intent_name,  message)


# Function to dispatch intent
def dispatch(intent_request):

    intent_name = intent_request['sessionState']['intent']['name']

    logger.debug(f'Intent Name: {intent_name}')
    if intent_name == 'DiningSuggestionsIntent':
        response =  dining_suggestion(intent_request)
        logger.debug(f"response of dining_suggestion: {response}")
        return response
    elif intent_name =='GreetingIntent':
        return greeting_intent(intent_request)

    elif intent_name =='ThankYouIntent':
        return thankyou_intent(intent_name)
        
    raise Exception('Intent with name ' + intent_name + ' not supported')

# Lambda handler
def lambda_handler(event, context):
    logger.debug('event.bot.name={}'.format(event['bot']['name']))
    logger.info(event)
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    return dispatch(event)