class CmdSetError(Exception):
    def __init__(self, error_message):
        self.error_message = error_message
        super().__init__(self.error_message)
