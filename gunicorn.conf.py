"""
Gunicorn configuration for Railway deployment
Optimized for handling email operations and preventing worker timeouts
"""

import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"
backlog = 2048

# Worker processes
workers = 2  # For Railway's resource constraints
worker_class = "sync"
worker_connections = 1000
timeout = 120  # Increased timeout for email operations
keepalive = 5

# Restart workers after this many requests to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
loglevel = "info"
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "lusitohub"

# Worker timeout handling
graceful_timeout = 30
kill_timeout = 5

# Preload app for better memory usage
preload_app = True

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190