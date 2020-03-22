import os

from sqlalchemy import Column, String, Integer, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
engine = create_engine(os.environ.get('SQLALCHEMY_DATABASE_URI'))
Session = sessionmaker(bind=engine)


class Record(Base):
    __tablename__ = 'records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_name = Column(String(200))
    room_name = Column(String(200), nullable=False)
    date = Column(String, nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)

    event_id = Column(String(200))

    def __init__(self, **kwargs):
        self.event_name = kwargs.get('event_name')
        self.room_name = kwargs.get('room_name')
        self.date = kwargs.get('date')
        self.start_time = kwargs.get('start_time')
        self.end_time = kwargs.get('end_time')
        self.event_id = kwargs.get('event_id')

    def update(self, **kwargs):
        self.event_id = kwargs.get('id')
        self.event_name = kwargs.get('summary')
        self.date = kwargs['start']['dateTime'].split('T')[0]
        self.start_time = kwargs['start']['dateTime'].split('T')[1][:5]
        self.end_time = kwargs['end']['dateTime'].split('T')[1][:5]
        self.room_name = kwargs['room_name']


class Room(Base):
    __tablename__ = 'rooms'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    tracking_state = Column(Boolean, default=False)
    drive = Column(String(200))
    calendar = Column(String(200))

    sound_source = Column(String(100))
    main_source = Column(String(100))
    tracking_source = Column(String(100))
    screen_source = Column(String(100))

    auto_control = Column(Boolean, default=True)
