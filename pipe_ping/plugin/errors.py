from pipe_ping.errors import PipePingError


class PipePingPluginError(PipePingError): ...


class NoPluginsConfiguredError(PipePingPluginError, ImportError):
    """Raised when a plugin group has no plugins installed."""


class PluginIsUniqueError(PipePingPluginError, RuntimeError):
    """Raised when a group that allows one plugin has several installed."""


class AllPluginsFailedError(PipePingPluginError, RuntimeError):
    """Raised when every plugin in a group fails to load."""


class PluginUnavailableError(PipePingPluginError, RuntimeError):
    """Raised from ``setup`` when a plugin is not configured or cannot run."""
