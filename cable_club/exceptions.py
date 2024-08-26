"""Custom exceptions used accross the application."""


class CableClubError(Exception):
    """Base class for all exceptions in the server."""


# misc
class ExhaustedReaderError(CableClubError):
    """Tried to read when there's no more data left."""


# model
class ModelError(CableClubError):
    """Base class for model-related errors."""


class ValidationError(ModelError):
    """Custom class to flag values that dont match contraints."""


class UnknownFieldError(ModelError):
    """Custom class to flag an attempt to assign an unknown field to a model."""


class UninitializedFieldError(ModelError):
    """Custom class to flag that a model's field was not init."""


# config
class ConfigError(CableClubError):
    """Base class for config-related errors."""


class ConfigLockedError(ConfigError):
    """Tried to assign a value to a configuration."""


class BadConfigurationError(ConfigError):
    """Some configuration is wrong."""
