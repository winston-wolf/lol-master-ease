from threading import Thread

class SimpleThread(object):
    process_class = Thread

    def __init__(self, function, *args, **kwargs):
        self.results = []
        self.thread = self.process_class(target=SimpleThread.run, args=(self.results, function, args, kwargs))
        self.thread.start()

    @staticmethod
    def run(results, function, args, kwargs):
        result = None
        exception = None

        try:
            result = function(*args, **kwargs)
        except Exception as e:
            exception = e

        results.append(result)
        results.append(exception)

    def result(self):
        self.thread.join()

        result, exception = self.results
        if exception:
            raise exception

        return result
