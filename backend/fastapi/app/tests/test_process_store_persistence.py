"""Process-local stores survive a restart; secret-bearing stores are never written."""
from __future__ import annotations

from pathlib import Path

from backend.fastapi.app import process_store_persistence as psp


def _persistence(tmp_path: Path, stores: dict):
    return psp.ProcessStorePersistence(backend=psp.FileBackend(tmp_path / 'state.json'), stores=stores)


def test_snapshot_round_trip_fills_stores_in_place(tmp_path: Path) -> None:
    contacts: list = [{'id': 1, 'tenant_id': 't1', 'name': 'Ada'}]
    kits: dict = {'t1': {'colors': {'primary': '#2563C9'}}}
    first = _persistence(tmp_path, {'contacts': contacts, 'kits': kits})
    assert first.flush() == 2

    # A new process starts with empty stores holding the same identities.
    contacts_after: list = []
    kits_after: dict = {}
    held = contacts_after
    second = _persistence(tmp_path, {'contacts': contacts_after, 'kits': kits_after})
    assert second.restore() == 2
    assert held is contacts_after and held == [{'id': 1, 'tenant_id': 't1', 'name': 'Ada'}]
    assert kits_after == {'t1': {'colors': {'primary': '#2563C9'}}}


def test_only_changed_stores_are_rewritten(tmp_path: Path) -> None:
    store: list = [{'id': 1}]
    persistence = _persistence(tmp_path, {'a': store, 'b': []})
    assert persistence.flush() == 1  # the empty store is not written
    assert persistence.flush() == 0
    store.append({'id': 2})
    assert persistence.flush() == 1


def test_emptied_store_overwrites_its_old_snapshot(tmp_path: Path) -> None:
    store: list = [{'id': 1}]
    first = _persistence(tmp_path, {'a': store})
    first.flush()
    store.clear()
    first.flush()
    fresh: list = []
    second = _persistence(tmp_path, {'a': fresh})
    second.restore()
    assert fresh == []


def test_corrupt_snapshot_is_skipped_not_fatal(tmp_path: Path) -> None:
    backend = psp.FileBackend(tmp_path / 'state.json')
    backend.save('a', '{not json')
    backend.save('b', '[1, 2]')
    a: list = []
    b: list = []
    assert psp.ProcessStorePersistence(backend=backend, stores={'a': a, 'b': b}).restore() == 1
    assert a == [] and b == [1, 2]


def test_secret_bearing_stores_are_excluded() -> None:
    for name in ('crm_api_tokens', 'rank_tracker._oauth_sessions', 'x._provider_config', 'ira_sessions', 'api_key_cache'):
        assert not psp.is_persistable(name.rsplit('.', 1)[-1]), name
    for name in ('crm_contacts', '_kits', 'playbooks'):
        assert psp.is_persistable(name), name


def test_discovery_names_known_stores_and_skips_secrets() -> None:
    names = set(psp.discover_stores())
    assert 'memory_stores.crm_contacts' in names
    assert 'routers.brandkit._kits' in names
    assert not any('api_tokens' in name or 'oauth' in name for name in names)


def test_database_backend_round_trip(tmp_path: Path, monkeypatch) -> None:
    """The SQL path, run against SQLite, upserts and reads back."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(f'sqlite:///{tmp_path / "db.sqlite"}')
    factory = sessionmaker(bind=engine)

    import contextlib

    @contextlib.contextmanager
    def session_scope():
        session = factory()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    monkeypatch.setattr('backend.fastapi.app.database.get_db_session', session_scope)
    backend = psp.DbBackend()
    backend.save('a', '[1]')
    backend.save('a', '[1,2]')
    assert backend.load_all() == {'a': '[1,2]'}


def test_stores_with_objects_or_datetimes_are_not_persisted(tmp_path: Path) -> None:
    import datetime as dt
    from dataclasses import dataclass

    @dataclass
    class Brand:
        name: str

    objects: dict = {'t1': [Brand('Acme')]}
    stamped: list = [{'when': dt.datetime(2026, 1, 1)}]
    plain: list = [{'ok': True}]
    persistence = _persistence(tmp_path, {'objects': objects, 'stamped': stamped, 'plain': plain})
    assert persistence.flush() == 1
    assert set(persistence.backend.load_all()) == {'plain'}


def test_brand_hub_models_round_trip(tmp_path: Path) -> None:
    from backend.fastapi.app.contexts.brand_management.public import Brand

    brand = Brand(tenant_id='t1', name='Acme', website='https://acme.test')
    store: dict = {brand.id: brand}
    name = 'memory_stores.brand_hub_brands'
    assert _persistence(tmp_path, {name: store}).flush() == 1
    fresh: dict = {}
    assert _persistence(tmp_path, {name: fresh}).restore() == 1
    restored = fresh[brand.id]
    assert isinstance(restored, Brand) and restored.name == 'Acme' and restored.created_at == brand.created_at
