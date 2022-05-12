class CustomException(Exception):
    def __init__(self, value, data):
        self.value = value
        self.data = data

    # __str__ is to print() the value
    def __str__(self):
        return(repr(self.value))
