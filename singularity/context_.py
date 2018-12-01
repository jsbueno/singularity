
# TODO
# This has to become a context-local variable
active_context = None

class Context:
    def __init__(self):
        self.data = {}
        # self.backend = None


class MemoryContext(Context):

    def __init__(self):
        self.backend = "memory"
        super().__init__()

def get_context():
    global active_context
    # TODO: fetch configuration from env-vars
    if not active_context:
        active_context = MemoryContext()
    return active_context



