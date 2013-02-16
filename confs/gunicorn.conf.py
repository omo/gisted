import multiprocessing
import os

prod_dir = "/home/ubuntu/work/gisted/"
worker = multiprocessing.cpu_count() * 2 + 1

if os.environ.get("GISTED_PROD"):
    user = "ubuntu"
    group = "ubuntu"
    bind = "0.0.0.0:8100"
    accesslog  = os.path.join(prod_dir, "log/access.log")
    errorlog   = os.path.join(prod_dir, "log/error.log")
    pidfile    = os.path.join(prod_dir, "run/gunicorn.pid")
    #debug = True
else:
    accesslog  = '-'
    errorlog   = '-'
    bind = "0.0.0.0:8100"
    debug = True
