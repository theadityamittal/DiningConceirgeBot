
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
