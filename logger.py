import logging
from io import StringIO

# global var
settings = {
    "CONSOLE": False
}

# Create a StringIO object to capture logs
log_output = StringIO()

# Set up a logger
logger = logging.getLogger('MyLogger')
logger.setLevel(logging.DEBUG)

class ConsoleFilter(logging.Filter):
    def filter(self, record):
        # Log to console if 'to_console' is True
        return getattr(record, 'to_console', False)

class StringIOFilter(logging.Filter):
    def filter(self, record):
        # Log to StringIO if 'to_console' is False or not present
        return not getattr(record, 'to_console', False)

# Create handlers
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.addFilter(ConsoleFilter())

stringio_handler = logging.StreamHandler(log_output)
stringio_handler.setLevel(logging.DEBUG)
stringio_handler.addFilter(StringIOFilter())

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(stringio_handler)