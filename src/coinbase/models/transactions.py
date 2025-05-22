import os
from sqlalchemy import (
    Column,
    String,
    Numeric,
    DateTime,
    Enum as SQLEnum,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import declarative_base
from enum import Enum

Base = declarative_base()

class BrokerType(Enum):
    coinbase = "Coinbase"
    schwab = "Schwab"


class Transaction(Base):
    __tablename__ = "transactions"

    tx_id    = Column(String(64), primary_key=True)
    asset    = Column(String(10), nullable=False)
    quantity = Column(Numeric(28, 8), nullable=False)
    cost_usd = Column(Numeric(28, 8), nullable=False)
    tx_type = Column(String(32), nullable=False)
    tx_time  = Column(DateTime, nullable=False)
    account_id = Column(String(64), nullable=False)    
    broker     = Column(SQLEnum(BrokerType), nullable=False)
