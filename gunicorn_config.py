import multiprocessing

# Server socket
bind = "0.0.0.0:10000"

# Worker processes
workers = 2
worker_class = "sync"
worker_connections = 1000

# Timeout - CRITICAL: Increase to 10 minutes for large file uploads
timeout = 600
graceful_timeout = 600
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "fpl-analyzer"

# Restart workers after this many requests (prevent memory leaks)
max_requests = 100
max_requests_jitter = 10
