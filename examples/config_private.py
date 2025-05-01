"""
Private config
"""

# Oracle Vector Store
VECTOR_DB_USER = "VOLVO_AGENTS"
VECTOR_DB_PWD = "VolvoVolvo2025##"
VECTOR_WALLET_PWD = "welcome1"
VECTOR_DSN = "adbv01_medium"
VECTOR_WALLET_DIR = "/Users/lsaetta/Progetti/volvo_parts_agent/wallet"

CONNECT_ARGS = {
    "user": VECTOR_DB_USER,
    "password": VECTOR_DB_PWD,
    "dsn": VECTOR_DSN,
    "config_dir": VECTOR_WALLET_DIR,
    "wallet_location": VECTOR_WALLET_DIR,
    "wallet_password": VECTOR_WALLET_PWD,
}

# integration with APM (in lsaetta-apm compartment)
APM_PUBLIC_KEY = "6OXZ45BTT5AHD5KYICGOMLXXAZYTTLGT"

