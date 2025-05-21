from sqlalchemy import (
    Column,
    String,
    Numeric,
    DateTime,
    Enum as SQLEnum,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import declarative_base
from models.transactions import BrokerType
Base = declarative_base()

class Lot(Base):
    __tablename__ = "Lot"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    account_id  = Column(String(64), nullable=False)
    tx_id       = Column(String(64), nullable=False)
    asset       = Column(String(64), nullable=False)
    quantity    = Column(Numeric(28,8), nullable=False)
    cost    = Column(Numeric(28,8), nullable=False)
    remaining   = Column(Numeric(28,8), nullable=False)
    broker     = Column(SQLEnum(BrokerType), nullable=False)
    buy_time    = Column(DateTime(timezone=True), nullable=False)
