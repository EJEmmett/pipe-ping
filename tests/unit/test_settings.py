from pipe_ping.tools.settings import CONFIG_FILE, PipePingSettings


def test_user_config_is_read_before_local_env():
    assert PipePingSettings.model_config["env_file"] == (CONFIG_FILE, ".env")


def test_local_env_overrides_user_config(tmp_path, monkeypatch):
    monkeypatch.delenv("PIPE_PING_GITHUB__REPOS", raising=False)
    user_config = tmp_path / "config.env"
    user_config.write_text(
        'PIPE_PING_GITHUB__REPOS=["owner/user"]\nPIPE_PING_GITHUB__RUNS_PER_REPO=5\n'
    )
    local_env = tmp_path / ".env"
    local_env.write_text('PIPE_PING_GITHUB__REPOS=["owner/local"]\n')

    settings = PipePingSettings(_env_file=(user_config, local_env))

    assert settings.github.repos == ["owner/local"]
    assert settings.github.runs_per_repo == 5


def test_plugin_settings_in_shared_config_are_ignored(tmp_path, monkeypatch):
    monkeypatch.delenv("PIPE_PING_GITHUB__REPOS", raising=False)
    config = tmp_path / "config.env"
    config.write_text(
        'PIPE_PING_GITHUB__REPOS=["owner/repo"]\nPIPE_PING_EXAMPLE_SETTING=value\n'
    )

    settings = PipePingSettings(_env_file=config)

    assert settings.github.repos == ["owner/repo"]
