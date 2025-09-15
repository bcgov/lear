import time


def pre_fork(server, worker):
    # Delay loading of each worker by 5 seconds
    # This is done to work around an issue where the Traction API is returning an invalid token. The issue happens
    # when successive token retrieval calls are made with less than 2-3 seconds between the calls.
    time.sleep(5)

def post_fork(server, worker):
    """Reinitialize LaunchDarkly client in the forked worker (required when using --preload)."""
    try:
        # Import inside the hook so it runs in the child process
        import ldclient
        client = ldclient.get()
        # Start LD background threads in the child process
        client.postfork()
        server.log.info("LaunchDarkly postfork() completed for worker pid=%s", worker.pid)
    except Exception as e:  # noqa: BLE001
        server.log.error("LaunchDarkly postfork() failed in worker pid=%s: %s", worker.pid, e)

def worker_exit(server, worker):
    """Flush and close LaunchDarkly client on worker shutdown."""
    try:
        import ldclient
        ldclient.get().close()
        server.log.info("LaunchDarkly client closed for worker pid=%s", worker.pid)
    except Exception:  # safe to ignore if client wasn't created
        pass
