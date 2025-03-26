from .journey import journey_blueprint
from routes.depricated.event import event_blueprint
from .paths import paths_blueprint
from ._customer_journey import customer_journey_blueprint
from .person import person_blueprint
from .utils import utils_blueprint
from .ph_events import posthog_events_blueprint

# Expose the blueprints so they can be imported from routes
__all__ = ['journey_blueprint', 'event_blueprint', 'paths_blueprint', 'customer_journey_blueprint', 'person_blueprint', 'utils_blueprint', 'posthog_events_blueprint']
