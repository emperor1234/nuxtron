"""Tests for config.settings._parse_database_url / _build_databases.

DATABASE_URL support was added so both services can be configured from a
single connection string (matching how app.database._get_database_url
already works on the FastAPI side) instead of requiring discrete
POSTGRES_HOST/USER/PASSWORD/etc vars.
"""
from __future__ import annotations

from unittest.mock import patch

from config.settings import _build_databases, _parse_database_url


class TestParseDatabaseUrl:
    def test_parses_all_components(self) -> None:
        result = _parse_database_url('postgresql://myuser:mypass@dbhost.internal:5432/nuxtron')
        assert result['ENGINE'] == 'django.db.backends.postgresql'
        assert result['NAME'] == 'nuxtron'
        assert result['USER'] == 'myuser'
        assert result['PASSWORD'] == 'mypass'
        assert result['HOST'] == 'dbhost.internal'
        assert result['PORT'] == '5432'
        assert result['sslmode'] is None

    def test_decodes_url_encoded_password(self) -> None:
        result = _parse_database_url('postgresql://myuser:myp%40ss@dbhost.internal:5432/nuxtron')
        assert result['PASSWORD'] == 'myp@ss'

    def test_extracts_sslmode_query_param(self) -> None:
        result = _parse_database_url('postgresql://u:p@host:5432/db?sslmode=require')
        assert result['sslmode'] == 'require'

    def test_defaults_port_when_missing(self) -> None:
        result = _parse_database_url('postgresql://u:p@host/db')
        assert result['PORT'] == '5432'

    def test_defaults_name_when_missing(self) -> None:
        result = _parse_database_url('postgresql://u:p@host:5432/')
        assert result['NAME'] == 'nuxtron'

    def test_empty_user_and_password_when_absent(self) -> None:
        result = _parse_database_url('postgresql://host:5432/db')
        assert result['USER'] == ''
        assert result['PASSWORD'] == ''


class TestBuildDatabases:
    def test_database_url_takes_priority_over_discrete_vars(self) -> None:
        env = {
            'DATABASE_URL': 'postgresql://urluser:urlpass@urlhost:5432/urldb',
            'POSTGRES_HOST': 'discretehost',
            'POSTGRES_USER': 'discreteuser',
        }
        with patch.dict('os.environ', env, clear=False):
            databases = _build_databases()
        default = databases['default']
        assert default['HOST'] == 'urlhost'
        assert default['USER'] == 'urluser'
        assert default['NAME'] == 'urldb'

    def test_falls_back_to_discrete_vars_when_no_url(self) -> None:
        env = {
            'DATABASE_URL': '',
            'POSTGRES_HOST': 'discretehost',
            'POSTGRES_USER': 'discreteuser',
            'POSTGRES_DB': 'discretedb',
        }
        with patch.dict('os.environ', env, clear=False):
            databases = _build_databases()
        default = databases['default']
        assert default['HOST'] == 'discretehost'
        assert default['USER'] == 'discreteuser'
        assert default['NAME'] == 'discretedb'

    def test_falls_back_to_sqlite_when_neither_set(self) -> None:
        env = {'DATABASE_URL': '', 'POSTGRES_HOST': ''}
        with patch.dict('os.environ', env, clear=False):
            databases = _build_databases()
        assert databases['default']['ENGINE'] == 'django.db.backends.sqlite3'

    def test_database_url_sslmode_overrides_env_var(self) -> None:
        env = {
            'DATABASE_URL': 'postgresql://u:p@host:5432/db?sslmode=disable',
            'POSTGRES_SSLMODE': 'require',
        }
        with patch.dict('os.environ', env, clear=False):
            databases = _build_databases()
        assert databases['default']['OPTIONS']['sslmode'] == 'disable'
