from contextlib import contextmanager

@contextmanager
def get_session():
    '''
    Utilize context manager semantics to create 
    a DB instance and automatically commit/rollback and
    close upon context loss.
    '''
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
