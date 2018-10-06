import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# an Engine, which the Session will use for connection
# resources
engine = create_engine(os.getenv("DB_CONN_STR"))

# create a configured "Session" class
Session = sessionmaker(bind=engine)

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    with session_scope() as session:
        session.execute("""
        create table if not exists Token (
            access_token varchar(100),
            expires_on datetime
        )""")
