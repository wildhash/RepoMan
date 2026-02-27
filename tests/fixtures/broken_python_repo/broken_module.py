"""A broken Python module for testing purposes."""


def divide(a, b):
    return a / b  # ZeroDivisionError not handled


def get_secret():
    # Exposed hardcoded secret — bad practice
    return "supersecret123"


def load_data(filename):
    f = open(filename)  # Not closed, no error handling
    return f.read()
