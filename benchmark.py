import timeit

setup = """
event_type = 'session.status'
status = 'TIMEOUT'
"""

stmt_list = """
event_type == 'session.status' and status in ['STOPPED', 'FAILED', 'DISCONNECTED', 'UNPAIRED', 'TIMEOUT']
"""

stmt_set = """
event_type == 'session.status' and status in {'STOPPED', 'FAILED', 'DISCONNECTED', 'UNPAIRED', 'TIMEOUT'}
"""

list_time = timeit.timeit(stmt_list, setup=setup, number=10000000)
set_time = timeit.timeit(stmt_set, setup=setup, number=10000000)

print(f"List time: {list_time:.5f}s")
print(f"Set time:  {set_time:.5f}s")
if list_time > 0:
    print(f"Improvement: {(list_time - set_time) / list_time * 100:.2f}%")
