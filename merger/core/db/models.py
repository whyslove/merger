import os

from sqlalchemy import Column, String, Integer, Boolean, create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()
engine = create_engine(os.environ.get('SQLALCHEMY_DATABASE_URI'))
Session = sessionmaker(bind=engine)


class Record(Base):
    __tablename__ = 'records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_name = Column(String(200))
    room_name = Column(String(200), nullable=False)
    date = Column(String(100), nullable=False)
    start_time = Column(String(100), nullable=False)
    end_time = Column(String(100), nullable=False)
    user_email = Column(String(100), nullable=False)
    event_id = Column(String(200))
    drive_file_url = Column(String(200))

    done = Column(Boolean, nullable=False, default=False)
    processing = Column(Boolean, nullable=False, default=False)
    error = Column(Boolean, nullable=False, default=False)


class Room(Base):
    __tablename__ = 'rooms'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    tracking_state = Column(Boolean, default=False)
    sources = relationship('Source', backref='room', lazy=False)
    drive = Column(String(200))
    calendar = Column(String(200))

    sound_source = Column(String(100))
    main_source = Column(String(100))
    tracking_source = Column(String(100))
    screen_source = Column(String(100))

    auto_control = Column(Boolean, default=True)


class Source(Base):
    __tablename__ = 'sources'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), default='источник')
    ip = Column(String(200))
    port = Column(String(200))
    rtsp = Column(String(200), default='no')
    audio = Column(String(200))
    merge = Column(String(200))
    tracking = Column(String(200))
    room_id = Column(Integer, ForeignKey('rooms.id'))
