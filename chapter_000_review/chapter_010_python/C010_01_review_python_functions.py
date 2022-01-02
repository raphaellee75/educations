

def parallel_print(p_args):
    import datetime
    import numpy
    import time
    index_value = p_args['index']
    sleep_time = numpy.random.rand()
    print(index_value, 'START', datetime.datetime.today(), sleep_time, flush=True)
    time.sleep(sleep_time)
    print(index_value, 'FINISH', datetime.datetime.today(), sleep_time, flush=True)
