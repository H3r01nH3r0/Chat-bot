import json
import requests

AMPLITUDE_API_KEY = "a0f3dd07ea2a7a773204ec21e912e4ce"
AMPLITUDE_ENDPOINT = "https://api.amplitude.com/2/httpapi"

def statistics(user_id, event_name):
    amp_event = {
        "user_id": user_id,
        "event_type": event_name,
        "platform": 'Telegram',
    }

    _ = requests.post(AMPLITUDE_ENDPOINT, data=json.dumps({
        'api_key': AMPLITUDE_API_KEY,
        'events': [amp_event],
    }))