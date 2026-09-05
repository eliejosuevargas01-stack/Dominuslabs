import timeit

def list_check(method):
    return method in ["POST", "PUT", "PATCH"]

def set_check(method):
    return method in {"POST", "PUT", "PATCH"}

METHODS = {"POST", "PUT", "PATCH"}
def global_set_check(method):
    return method in METHODS

if __name__ == "__main__":
    for m in ["GET", "POST", "PATCH", "DELETE"]:
        print(f"Benchmarking {m}")
        print("List:", timeit.timeit(f'list_check("{m}")', globals=globals(), number=10000000))
        print("Set:", timeit.timeit(f'set_check("{m}")', globals=globals(), number=10000000))
        print("Global Set:", timeit.timeit(f'global_set_check("{m}")', globals=globals(), number=10000000))
