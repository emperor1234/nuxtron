# Nuxtron backend gunicorn config. Loaded when gunicorn is started with
# `--config gunicorn.conf.py`. Kept minimal; the Dockerfile's CMD already
# expresses the same knobs as flags so either path works.

import multiprocessing
import os

# Idle worker timeout (seconds). Keep below the load-balancer idle timeout.
timeout = int(os.getenv('GUNICORN_TIMEOUT', '30'))
graceful_timeout = int(os.getenv('GUNICORN_GRACEFUL_TIMEOUT', '30'))

# `WEB_CONCURRENCY` is conventionally set by the platform (e.g. Heroku/Render).
workers = int(os.getenv('WEB_CONCURRENCY', str((multiprocessing.cpu_count() * 2) + 1)))
threads = int(os.getenv('WEB_THREADS', '4'))

# Recycle workers to defragment memory / catch slow leaks.
max_requests = int(os.getenv('GUNICORN_MAX_REQUESTS', '1000'))
max_requests_jitter = 100

bind = os.getenv('GUNICORN_BIND', '0.0.0.0:8000')
preload_app = True

accesslog = '-'   # stdout
errorlog = '-'    # stderr
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')
