from pathlib import Path

from redis import Redis

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

REDIS_HOST = "localhost"
REDIS_PORT = 6379
STREAM = "payments"
GROUP = "payment-workers"
SIMULATED_CHARGES_KEY = "simulated_charges"
CHARGES_LOG = DATA_DIR / "charges.log"


def redis_client() -> Redis:
    return Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
