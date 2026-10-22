"""Shared, bounded in-process execution capacity for resource pipelines."""
from concurrent.futures import ThreadPoolExecutor

RESOURCE_WORKERS = 2
_executor = ThreadPoolExecutor(max_workers=RESOURCE_WORKERS, thread_name_prefix='plex-resource')


def submit_resource_task(function, *args):
    return _executor.submit(function, *args)
