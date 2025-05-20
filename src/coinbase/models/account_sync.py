from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class AccountSync(Base):
    __tablename__ = "account_sync"

    account_id    = Column(String(64), primary_key=True)
    asset         = Column(String(20), nullable=False)
    last_tx_time  = Column(DateTime(timezone=True), nullable=True)
