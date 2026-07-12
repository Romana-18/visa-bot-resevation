import threading

# Database URI (if using database features)
URI = 'postgresql://username:password@localhost:5432/almaviva_db?sslmode=require'

# Legacy credentials (not used in web interface)
ID = ''
USERNAME = ''
PASSWORD = ''

# Threading
Thread_Pool: list[threading.Thread] = []
MAIN_FLAG = 1
FIRST_RUN = False
