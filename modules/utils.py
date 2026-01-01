from functools import wraps

def run_every_n_calls(n: int):
    def decorator(func):
        call_count = 0
        cached = None
        has_value = False

        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal call_count, cached, has_value

            call_count += 1

            if call_count % n == 0 or not has_value:
                cached = func(*args, **kwargs)
                has_value = True

            return cached

        return wrapper
    return decorator
