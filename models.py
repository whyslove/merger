import os

from sqlalchemy import Column, String, Integer, Date, Time, Boolean, create_engine
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
    folder_id = Column(String(200), nullable=False)
    event_src = Column(String(200))
    event_id = Column(String(200))

    def update(self, **kwargs):
        new_record.event_id = kwargs['id']
        new_record.event_src = kwargs['htmlLink']
        new_record.event_name = kwargs.get('summary')
        new_record.date = kwargs['start']['dateTime'].split('T')[0]
        new_record.start_time = kwargs['start']['dateTime'].split('T')[1][:5]
        new_record.end_time = kwargs['end']['dateTime'].split('T')[1][:5]
        new_record.room_name = kwargs['room_name']
        new_record.folder_id = ''
