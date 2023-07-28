import multiprocessing

max_requests = 1000
max_requests_jitter = 50
log_file = "-"
bind = "0.0.0.0"

num_cpus = multiprocessing.cpu_count()
workers = (num_cpus * 2) + 1
threads = 1 if num_cpus == 1 else 2
timeout = 600
