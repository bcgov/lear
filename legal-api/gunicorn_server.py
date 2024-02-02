"""This module is for delay loading"""
import time


def pre_fork(server, worker):
    """Delay loading of each worker by 5 seconds
    This is done to work around an issue where the Traction API is returning an invalid token. The issue happens
    when successive token retrieval calls are made with less than 2-3 seconds between the calls."""
    time.sleep(5)
