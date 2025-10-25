from .form_usage_routes import form_usage_blueprint
from .journey import journey_blueprint
from routes.depricated.event import event_blueprint
from .paths import paths_blueprint
from ._customer_journey import customer_journey_blueprint
from .person import person_blueprint
from .utils import utils_blueprint
from routes.depricated.ph_events import posthog_events_blueprint
from .events import events_blueprint
from .page_usage_routes import page_usage_blueprint
from .event_usage_routes import event_usage_blueprint
from .friction_routes import friction_blueprint
from .insights_routes import insights_blueprint
from .events_failed_routes import events_failed_blueprint
from .process_routes import process_blueprint

# Expose the blueprints so they can be imported from routes
__all__ = [
    'journey_blueprint', 'paths_blueprint', 'customer_journey_blueprint',
    'person_blueprint', 'utils_blueprint', 'posthog_events_blueprint',
    'events_blueprint', 'events_failed_blueprint', 'page_usage_blueprint',
    'event_usage_blueprint', 'friction_blueprint', 'form_usage_blueprint', 'insights_blueprint', 'process_blueprint'
]