from models.customer_journey import FrictionType


def detect_backtracking(raw_events):
    """Detect when users navigate back to previously visited pages"""
    friction_points = []

    # Group events by session
    sessions = {}
    for event in raw_events:
        if not event.session_id or not event.pathname:
            continue

        if event.session_id not in sessions:
            sessions[event.session_id] = []
        sessions[event.session_id].append(event)

    for session_id, events in sessions.items():
        visited_pages = []

        for event in events:
            current_page = event.pathname

            # Check if user returned to a previously visited page
            if current_page in visited_pages:
                # Find the last occurrence
                last_index = len(visited_pages) - 1 - visited_pages[::-1].index(current_page)
                steps_back = len(visited_pages) - last_index

                # Only consider significant backtracking (more than 1 step back)
                if steps_back > 1:
                    friction_points.append({
                        'account_id': event.account_id,
                        'session_id': session_id,
                        'event_name': 'backtracking',
                        'url': current_page,
                        'event_details': f"Returned to page after {steps_back} steps",
                        'friction_type': FrictionType.BACKTRACKING,
                        'volume': 1,
                        'user_dismissed': False
                    })

            visited_pages.append(current_page)

    return friction_points