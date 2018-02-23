import logging

from . import models


class LogStream(object):
    """File-like interface to Log model."""

    def __init__(self, model):
        self.model = model

    def flush(self, force=False):
        pass

    def write(self, message):
        models.Log.objects.create(
            content_object=self.model,
            message=message,
        )


def get_logger(model):
    """Get an instance of the logger."""
    logger_name = 'sfdoc_{}'.format(model.__class__.__name__)
    logger = logging.getLogger(logger_name)
    if logger.handlers:
        # already configured
        return logger
    logger.setLevel(logging.DEBUG)
    # create handlers
    handler = logging.StreamHandler(stream=LogStream(model))
    handler_console = logging.StreamHandler()
    # set handler levels
    handler.setLevel(logging.INFO)
    handler_console.setLevel(logging.ERROR)
    # add handlers to logger
    logger.addHandler(handler)
    logger.addHandler(handler_console)
    return logger
