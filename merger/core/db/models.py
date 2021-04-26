import os
import uuid
from datetime import datetime
import time

import jwt
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    create_engine,
    ForeignKey,
    DateTime,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import func
from sqlalchemy.orm import sessionmaker, relationship
from werkzeug.security import generate_password_hash, check_password_hash


Base = declarative_base()
engine = create_engine(os.environ.get("SQLALCHEMY_DATABASE_URI"))
Session = sessionmaker(bind=engine)


class IdMixin:
    id = Column(Integer, primary_key=True)


class TimeMixin:
    created_at = Column(DateTime, default=func.now())
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now())


class CommonMixin(IdMixin, TimeMixin):
    pass


class UserRecord(Base, TimeMixin):
    __tablename__ = "user_records"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    record_id = Column(Integer, ForeignKey("records.id"), primary_key=True)

    user = relationship("User", back_populates="records")
    record = relationship("Record", back_populates="users")


class Record(Base, CommonMixin):
    __tablename__ = "records"

    date = Column(String(100), nullable=False)
    start_time = Column(String(100), nullable=False)
    end_time = Column(String(100), nullable=False)
    event_name = Column(String(200))
    event_id = Column(String(200), unique=True)
    drive_file_url = Column(String(200))
    ruz_id = Column(Integer, unique=True)  # lessonOid from ruz API

    done = Column(Boolean, default=False)
    processing = Column(Boolean, default=False)
    error = Column(Boolean, default=False)

    room_id = Column(Integer, ForeignKey("rooms.id"))
    room = relationship("Room", back_populates="records")
    users = relationship("UserRecord", back_populates="record")

    def update_from_calendar(self, **kwargs):
        self.event_id = kwargs.get("id")
        self.event_name = kwargs.get("summary")
        self.date = kwargs["start"]["dateTime"].split("T")[0]
        self.start_time = kwargs["start"]["dateTime"].split("T")[1][:5]
        self.end_time = kwargs["end"]["dateTime"].split("T")[1][:5]

    def to_dict(self):
        return dict(
            id=self.id,
            date=self.date,
            start_time=self.start_time,
            end_time=self.end_time,
            event_name=self.event_name,
            event_id=self.event_id,
            drive_file_url=self.drive_file_url,
            room=self.room.to_dict(),
            done=self.done,
            processing=self.processing,
        )


class User(Base, CommonMixin):
    __tablename__ = "users"

    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(255), default=None)
    email_verified = Column(Boolean, default=False)
    access = Column(Boolean, default=False)
    api_key = Column(String(255), unique=True)
    last_login = Column(DateTime, default=datetime.utcnow)

    banned = Column(Boolean, default=False)

    records = relationship("UserRecord", back_populates="user", lazy="joined")

    organization_id = Column(Integer, ForeignKey("organizations.id"))
    organization = relationship("Organization", back_populates="users", lazy="joined")

    role_id = Column(Integer, ForeignKey("roles.id"))
    role = relationship("Role", back_populates="users", lazy="joined")

    def __init__(self, email, organization_id, password=None):
        self.email = email
        self.organization_id = organization_id
        if password:
            self.password = generate_password_hash(password, method="sha256")

    def update_pass(self, password):
        self.password = generate_password_hash(password, method="sha256")

    @classmethod
    def authenticate(cls, session, **kwargs):
        email = kwargs.get("email")
        password = kwargs.get("password")

        if not email or not password:
            return None

        user = session.query(cls).filter_by(email=email).first()
        if (
            not user
            or not user.password
            or not check_password_hash(user.password, password)
        ):
            return None

        return user

    @classmethod
    def create_api_key(cls, user_id):
        session = Session()
        api_key = session.query(cls).get(user_id).api_key
        session.close()

        if api_key:
            return
        return uuid.uuid4().hex

    def get_token(self, token_expiration: int, key: str):
        """
        Creates verification token
        """
        return jwt.encode(
            {key: self.id, "exp": time.time() + token_expiration},
            os.environ.get("SECRET_KEY"),
            algorithm="HS256",
        ).decode("utf-8")

    def delete_user_after_token_expiration(self, app, token_expiration: int) -> None:
        """
        Deletes user if token is expired
        """
        # TODO looks weird
        time.sleep(token_expiration)
        session = Session()
        user = session.query(User).get(self.id)
        if not user.email_verified:
            session.delete(user)
            session.commit()
        session.close()

    @staticmethod
    def verify_token(session: Session, token: str, key: str):
        """
        Check if token is valid
        """
        try:
            id = jwt.decode(token, os.environ.get("SECRET_KEY"), algorithms=["HS256"])[
                key
            ]
        except Exception:
            return

        user = session.query(User).get(id)
        return user

    def to_dict(self):
        return dict(
            id=self.id,
            email=self.email,
            email_verified=self.email_verified,
            access=self.access,
            last_login=str(self.last_login),
            banned=self.banned,
            online=False,
            role=self.role.name,
        )


class Room(Base, CommonMixin):
    __tablename__ = "rooms"

    name = Column(String(100), nullable=False)
    ruz_id = Column(Integer)

    drive = Column(String(200))
    calendar = Column(String(200))

    sound_source = Column(String(100))
    main_source = Column(String(100))
    screen_source = Column(String(100))

    auto_control = Column(Boolean, default=True)

    records = relationship("Record", back_populates="room")
    sources = relationship("Source", backref="room")

    organization_id = Column(Integer, ForeignKey("organizations.id"))
    organization = relationship("Organization", back_populates="rooms", lazy="joined")

    def to_dict(self):
        return dict(
            id=self.id,
            name=self.name,
            sources=[source.to_dict() for source in self.sources],
            drive=self.drive,
            calendar=self.calendar,
            sound_source=self.sound_source,
            main_source=self.main_source,
            screen_source=self.screen_source,
            auto_control=self.auto_control,
        )


class OnlineRoom(Base, CommonMixin):
    __tablename__ = "online_rooms"

    name = Column(String(100), nullable=False, unique=True)
    calendar = Column(String(200))
    drive = Column(String(200))

    def to_dict(self):
        return dict(name=self.name, calendar=self.calendar, drive=self.drive)


class Source(Base, CommonMixin):
    __tablename__ = "sources"

    name = Column(String(100), default="источник")
    ip = Column(String(200))
    port = Column(String(200))
    rtsp = Column(String(200), default="no")
    audio = Column(String(200))
    merge = Column(String(200))
    room_id = Column(Integer, ForeignKey("rooms.id"))
    external_id = Column(String(200))

    def update(self, **kwargs):
        self.name = kwargs.get("name")
        self.ip = kwargs.get("ip")
        self.port = kwargs.get("port")
        self.rtsp = kwargs.get("rtsp")
        self.audio = kwargs.get("audio")
        self.merge = kwargs.get("merge")
        self.room_id = kwargs.get("room_id")
        self.external_id = kwargs.get("external_id")

    def to_dict(self):
        return dict(
            id=self.id,
            name=self.name,
            ip=self.ip,
            port=self.port,
            rtsp=self.rtsp,
            audio=self.audio,
            merge=self.audio,
            room_id=self.room_id,
            external_id=self.external_id,
        )


class Organization(Base, CommonMixin):
    __tablename__ = "organizations"

    name = Column(String(100), unique=True, nullable=False)

    users = relationship("User", back_populates="organization")
    rooms = relationship("Room", back_populates="organization")

    def to_dict(self):
        return dict(
            id=self.id,
            name=self.name,
        )


class Role(Base, CommonMixin):
    __tablename__ = "roles"

    name = Column(String(50), unique=True)

    users = relationship("User", back_populates="role")

    def to_dict(self):
        return dict(id=self.id, name=self.name)
