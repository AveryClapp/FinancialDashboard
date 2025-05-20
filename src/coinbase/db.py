from contextlib import contextmanager
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine

DATABASE_URL = "mysql+pymysql://root:@localhost:3306/FinancialDashboard"

engine = create_engine(DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(bind=engine, 
                    autoflush=False,
                    autocommit=False,
                    future=True)


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
