class CustomException(Exception):
    def __init__(self, value, data=None):
        self.value = value
        self.data = data

    # __str__ is to print() the value
    def __str__(self):
        return(repr(self.value))


class CustomUnsupportedTypeException(Exception):
    def __init__(self, value, data=None):
        self.value = value
        self.data = data

    # __str__ is to print() the value
    def __str__(self):
        return(repr(self.value))
