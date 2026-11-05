import os
import pytest

DSN = os.getenv('BELGIFLOW_TEST_DSN')
pytestmark = pytest.mark.skipif(not DSN, reason='set BELGIFLOW_TEST_DSN for disposable PostgreSQL')


def test_commit_order_replay_and_deletes(tmp_path):
    import psycopg
    from belgiflow.cdc import initialize, consume, changes
    initialize(DSN)
    with psycopg.connect(DSN) as reset:
        reset.execute('TRUNCATE delivery_ack,outbox,depot RESTART IDENTITY')
    first = psycopg.connect(DSN)
    second = psycopg.connect(DSN)
    try:
        first.execute("INSERT INTO depot(entity_id,capacity,effective_at,revision) VALUES ('DEPOT-A',100,'2026-01-01',1)")
        second.execute("INSERT INTO depot(entity_id,capacity,effective_at,revision) VALUES ('DEPOT-B',200,'2026-01-01',1)")
        second.commit()
        journal = tmp_path / 'cdc.sqlite'
        assert consume(DSN, journal) == 1
        first.commit()
        assert consume(DSN, journal) == 1
        with psycopg.connect(DSN) as con:
            con.execute("UPDATE depot SET capacity=150,revision=2 WHERE entity_id='DEPOT-A'")
            con.execute("DELETE FROM depot WHERE entity_id='DEPOT-B'")
        with pytest.raises(RuntimeError):
            consume(DSN, journal, fail_before_ack=True)
        assert consume(DSN, journal) == 2
        assert consume(DSN, journal) == 0
        assert [r['operation'] for r in changes(journal)] == ['INSERT','INSERT','UPDATE','DELETE']
    finally:
        first.close()
        second.close()
