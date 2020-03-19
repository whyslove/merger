import os

from sqlalchemy import Column, String, Integer, Date, Time, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
engine = create_engine(os.environ.get('SQLALCHEMY_DATABASE_URI'))
Session = sessionmaker(bind=engine)


class Record(Base):
    __tablename__ = 'records'

    id = Column(Integer, primary_key=True)
    event_name = Column(String(200))
    room_name = Column(String(200), nullable=False)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    event_src = Column(String(200))
    event_id = Column(String(200))
