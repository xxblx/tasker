
import multiprocessing

# Application
WORKERS = multiprocessing.cpu_count()
DEBUG = True
TOKEN_EXPIRES_TIME = 7200  # seconds

# HTTP Server
HOST = '127.0.0.1'
PORT = 8888

# Database
DB_SETTINGS = {
    'database': 'taskerdb',
    'user': 'taskeruser',
    'host': '/var/run/postgresql'
}
