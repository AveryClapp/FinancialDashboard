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

class Gain(Base):
    __tablename__ = "Gain"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    tx_id       = Column(String(64), nullable=False)
    asset       = Column(String(64), nullable=False)
    quantity = Column(Numeric(28,8), nullable=False)
    sell_price  = Column(Numeric(28,8), nullable=False)
    cost    = Column(Numeric(28,8), nullable=False)
    gain    = Column(Numeric(28,8), nullable=False)
    broker     = Column(SQLEnum(BrokerType), nullable=False)
    matched_at = Column(DateTime(timezone=True), nullable=False)
