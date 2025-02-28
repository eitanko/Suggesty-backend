import pytest
from app import app

@pytest.fixture(scope="module")
def client():
    with app.test_client() as client:
        yield client

@pytest.fixture(scope="module")
def registered_user(client):
    # Register a new user
    register_payload = {
        "uuid": None,
        "userAgent": "Unit test",
        "apiKey": "temp_api_key"
    }
    register_response = client.post('/api/person/register', json=register_payload)
    assert register_response.status_code == 201

    register_data = register_response.json
    person_id = register_data['personId']
    session_id = register_data['sessionId']
    return person_id, session_id

def test_event_track_new_CJ(client, registered_user):
    person_id, session_id = registered_user
    print(f"session_id: {session_id}, person_id: {person_id}")

    # Use the registered user's personId and sessionId to track an event
    track_payload = {
        "uuid": person_id,
        "sessionId": session_id,
        "url": "https://project-management-app-cyan.vercel.app/",
        "eventType": "mouseup",
        "element": {
            "tagName": "A",
            "eventType": "mousedown",
            "innerText": "Participants",
            "attributes": {
                "aria-label": "Go to Automations",
                "href": "/automations"
            },
            "xpath": "//a[@aria-label='Go to Automations']"
        }
    }
    track_response = client.post('/api/event/track', json=track_payload)
    assert track_response.status_code == 201
    track_data = track_response.json
    assert 'CJID' in track_data
    assert track_data['status'] == 'New journey started and event tracked'

def test_track_new_event(client, registered_user):
    person_id, session_id = registered_user
    print(f"session_id: {session_id}, person_id: {person_id}")

    # Use the registered user's personId and sessionId to track another event
    track_payload = {
        "uuid": person_id,
        "sessionId": session_id,
        "url": "https://project-management-app-cyan.vercel.app/participants",
        "eventType": "click",
        "element": {
            "tagName": "BUTTON",
            "eventType": "click",
            "innerText": "Join",
            "attributes": {
                "aria-label": "Join Participants",
                "href": "/join"
            },
            "xpath": "//button[@aria-label='Join Participants']"
        }
    }
    track_response = client.post('/api/event/track', json=track_payload)
    assert track_response.status_code == 200
    track_data = track_response.json
    assert 'CJID' in track_data
    assert track_data['status'] == 'Event tracked'