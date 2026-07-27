"""Constantes da integração Portaris."""

DOMAIN = "portaris"

DEFAULT_HOST = "https://app.portaris.app"

CONF_HOST = "host"
CONF_TOKEN = "token"

# Escopos que o token pode conceder (espelham IntegrationScopes no backend).
SCOPE_STATE_READ = "state:read"
SCOPE_DOOR_UNLOCK = "door:unlock"

# Intervalo de polling do estado (portas/leitores/eventos), em segundos.
# BASE em operação normal; sobe até MAX com backoff exponencial quando a API falha.
BASE_INTERVAL = 30
MAX_INTERVAL = 300

# Tipos de evento de acesso (espelham AccessEventType no backend).
EVENT_TYPES = [
    "Granted",
    "Denied",
    "DoorForced",
    "DoorHeldOpen",
    "DeviceOffline",
    "DeviceOnline",
    "DoorOpened",
    "DoorClosed",
    "ManualUnlock",
]
