from db import db
from sqlalchemy.orm import joinedload
from models import CustomerJourney, Event, Step
import json
from urllib.parse import urlparse

def fetch_and_structure_user_journeys(journey_id):
    # Fetch user journeys related to the specific journey_id from the database
    user_journeys = (
        db.session.query(CustomerJourney)
        .options(joinedload(CustomerJourney.events))  # Efficient loading of events
        .filter(CustomerJourney.journey_id == journey_id)
        .all()
    )

    user_journeys_list = []

    # Iterate over the fetched user journeys
    for journey in user_journeys:
        events_dict = {}

        # Process each event in the journey
        for event in journey.events:
            element_data = json.loads(event.element)  # Parse element data
            xpath = element_data.get("xpath")
            event_type = element_data.get("eventType", "")

            # Extract the base URL and trimmed URL
            parsed_url = urlparse(event.url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            trimmed_url = event.url.replace(base_url, "", 1)  # Relative URL

            # Initialize the page URL entry if not already
            if trimmed_url not in events_dict:
                events_dict[trimmed_url] = {
                    'page_title': element_data.get("innerText", ""),
                    'actions': []
                }

            # Add the event data under the appropriate page
            events_dict[trimmed_url]['actions'].append({
                'timestamp': event.timestamp.timestamp(),
                'event_type': event_type,
                'element': element_data
            })

        # Sort actions by timestamp for each page URL
        for page_url in events_dict:
            events_dict[page_url]['actions'].sort(key=lambda e: e['timestamp'])

        # Append structured data to the user journeys list
        user_journeys_list.append({
            'journey_id': journey.id,
            'session_id': journey.session_id,
            'user_id': str(journey.person_id),
            'status': journey.status.value,
            'events': events_dict,
            'updated_at': journey.updated_at,
            'start_time': journey.start_time,
            'end_time': journey.end_time,
        })

    return user_journeys_list

# example output
# {
#     "journey_id": 82,
#     "session_id": "5263135a-ce15-478a-90d8-a382862a31ca",
#     "user_id": "011428b3-bfe7-45ab-be82-4127a5089d00",
#     "status": "COMPLETED",
#     "events": {
#         "/projects": {
#             "page_title": "Projects - My App",
#             "actions": [
#                 {
#                     "timestamp": 1741287786.625,
#                     "event_type": "click",
#                     "element": {
#                         "tagName": "A",
#                         "eventType": "mouseup",
#                         "innerText": "New Project",
#                         "attributes": {
#                             "href": "/projects/new"
#                         },
#                         "xpath": "//a[contains(., 'New Project')]"
#                     }
#                 }
#             ]
#         },
#         "/projects/new": {
#             "page_title": "New Project - My App",
#             "actions": [
#                 {
#                     "timestamp": 1741287789.936,
#                     "event_type": "input",
#                     "element": {
#                         "tagName": "INPUT",
#                         "eventType": "keydown",
#                         "attributes": {
#                             "name": "project_name",
#                             "type": "text"
#                         },
#                         "xpath": "//input[@name='project_name']"
#                     }
#                 },
#                 {
#                     "timestamp": 1741287817.365,
#                     "event_type": "click",
#                     "element": {
#                         "tagName": "BUTTON",
#                         "eventType": "click",
#                         "ariaLabel": "Save Project",
#                         "xpath": "//button[@aria-label='Save Project']"
#                     }
#                 }
#             ]
#         }
#     },
#     "start_time": "2025-03-06T21:03:06.231000",
#     "end_time": "2025-03-06T21:03:37.225000",
#     "updated_at": "2025-03-06T21:03:37.061000"
# }
