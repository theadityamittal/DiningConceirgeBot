from decimal import Decimal

def elicit_slot(session_state, slot_to_elicit, message=None):
    """
    This function builds a response that elicits a particular slot from the user.
    
    Parameters:
    session_state (dict): The session state of the user.
    slot_to_elicit (str): The name of the slot to elicit.
    message (dict): The message to be sent to the user to elicit the slot.
    
    Returns:
    dict: A dictionary containing the session state and the message to be sent to the user.
    """
    session_state['dialogAction'] =  {
            'type': 'ElicitSlot',
            'slotToElicit': slot_to_elicit
            }

    response = {
        'sessionState': session_state
    }    

    if message:
        response['messages'] = [message]
    return response


def confirm_intent(session_state, message=None):
    """
    This function builds a response that confirms the intent and elicits slot values from the user.

    Parameters:
    session_state (dict): The session state of the user.
    message (dict): The message to be sent to the user to elicit slot values.

    Returns:
    dict: A dictionary containing the session state and the message to be sent to the user.
    """
    session_state['dialogAction'] = {
        'type': 'ConfirmIntent'
        }
        
    return {
    'sessionState': session_state,
    'messages': [message] or []
    }



def close(intent_name, message):
    """
    This function builds a response that closes the intent and includes a message to be sent to the user.

    Parameters:
    intent_name (str): The name of the intent to be closed.
    message (dict): The message to be sent to the user.

    Returns:
    dict: A dictionary containing the session state and the message to be sent to the user.
    """
    session_state = {
        "dialogAction": {
            "type": "Close"
        },
        "intent": {
            "name": intent_name,
            "state": "Fulfilled"
        }
    }
    
    
    return {
        'sessionState': session_state,
        'messages': [message]
    }


def delegate(session_state):
    """
    This function delegates the next action to Lex.

    Parameters:
    session_state (dict): The session state of the user.

    Returns:
    dict: A dictionary containing the session state with the dialog action type set to "Delegate".
    """
    session_state["dialogAction"] = {
        "type": "Delegate"
    }
    return {
        'sessionState': session_state,
    }


# --- Helper Functions ---

def safe_int(n):
    """
    Safely convert n value to int.
    """
    if n is not None:
        return int(n)
    return n


def try_ex(func):
    """
    Call passed-in function in a try block. If KeyError is encountered, return None.
    This function is intended to be used to safely access dictionaries.
    """
    try:
        return func()
    except (KeyError, TypeError) as e:
        return None


def decimal_default(obj):
    """
    Convert Decimal objects to float, otherwise return the object as a string.

    Args:
        obj: The object to be converted.

    Returns:
        float if obj is a Decimal, otherwise str.
    """
    try:    
        if isinstance(obj, Decimal):
            return float(obj)
    except Exception as err:
        return str(obj)
        
        

def reorder_dict(d, key_order):
    """Reorder keys in a dictionary."""
    return {key: d[key] for key in key_order if key in d}

def dict_to_html_table(data, cuisine_type, location):
    """
    Converts a list of dictionaries to an HTML table.
    
    Args:
        data (list): List of dictionaries containing restaurant data.
        cuisine_type (str): Type of cuisine for the suggestions.
        location (str): Location for the suggestions.
    
    Returns:
        str: HTML table containing the restaurant suggestions.
    """
    html_table = f"""<html>
            <head></head>
            <body>
            <h1> Here is your suggestions for {cuisine_type.title()} restaurants in {location}</h1>.
            <table border='1'>"""

    html_table += "<tr>"
    for key in data[0].keys():
        html_table += f"<th>{key.title()}</th>"
    html_table += "</tr>"

    for item in data:
        html_table += "<tr>"
        for key, value in item.items():
            html_table += f"<td>{str(value).title()}</td>"
        html_table += "</tr>"

    html_table += """</table>
        <br><br>
        <p> Hope you like the suggestions.
                </body>
            </html>"""

    return html_table

