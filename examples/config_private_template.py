"""
Private config
"""

# Oracle Vector Store
VECTOR_DB_USER = "your-user"
VECTOR_DB_PWD = "your-pwd"
VECTOR_WALLET_PWD = "wallet-pwd"
VECTOR_DSN = "your-adb-dsn"
VECTOR_WALLET_DIR = "path-to-wallet-dir"

CONNECT_ARGS = {
    "user": VECTOR_DB_USER,
    "password": VECTOR_DB_PWD,
    "dsn": VECTOR_DSN,
    "config_dir": VECTOR_WALLET_DIR,
    "wallet_location": VECTOR_WALLET_DIR,
    "wallet_password": VECTOR_WALLET_PWD,
}

# integration with APM
APM_PUBLIC_KEY = "your-apm-public-key"

