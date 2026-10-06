import pytest
from pipe_ping.errors import PipePingError
from pipe_ping.plugin.errors import (
    AllPluginsFailedError,
    NoPluginsConfiguredError,
    PipePingPluginError,
    PluginIsUniqueError,
)


@pytest.mark.parametrize(
    ("exc_cls", "bases"),
    [
        (PipePingError, (Exception,)),
        (PipePingPluginError, (PipePingError,)),
        (NoPluginsConfiguredError, (PipePingPluginError, ImportError)),
        (PluginIsUniqueError, (PipePingPluginError, RuntimeError)),
        (AllPluginsFailedError, (PipePingPluginError, RuntimeError)),
    ],
)
def test_exception_hierarchy(exc_cls, bases):
    for base in bases:
        assert issubclass(exc_cls, base)


@pytest.mark.parametrize(
    "exc_cls",
    [
        PipePingError,
        PipePingPluginError,
        NoPluginsConfiguredError,
        PluginIsUniqueError,
        AllPluginsFailedError,
    ],
)
def test_exception_is_raiseable(exc_cls):
    with pytest.raises(exc_cls, match="test message"):
        raise exc_cls("test message")
