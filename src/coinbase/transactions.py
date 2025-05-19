import os
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Numeric,
    DateTime,
    Enum,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker
import enum

DATABASE_URL = "mysql+pymysql://root:@localhost:3306/FinancialDashboard"

engine = create_engine(DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(bind=engine, 
                    autoflush=False,
                    autocommit=False,
                    future=True)

Base = declarative_base()


class TxType(enum.Enum):
    buy = "buy"
    sell = "sell"


class Transaction(Base):
    __tablename__ = "transactions"

    tx_id    = Column(String(64), primary_key=True)
    asset    = Column(String(10), nullable=False)
    quantity = Column(Numeric(28, 8), nullable=False)
    cost_usd = Column(Numeric(28, 8), nullable=False)
    tx_type  = Column(Enum(TxType), nullable=False)
    tx_time  = Column(DateTime, nullable=False)
