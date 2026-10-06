from pipe_ping.errors import PipePingError


class PipePingPluginError(PipePingError): ...


class NoPluginsConfiguredError(PipePingPluginError, ImportError):
    """Raised when no plugins are located."""


class PluginIsUniqueError(PipePingPluginError, RuntimeError):
    """Raised when more than one unique plugin is located."""


class AllPluginsFailedError(PipePingPluginError, RuntimeError):
    """Raised when every plugin in a group fails to load."""


class PluginUnavailableError(PipePingPluginError, RuntimeError):
    """Raised during setup when a plugin's backing service is unavailable."""
