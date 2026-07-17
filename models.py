from typing import Optional

from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    username: str
    password: str


class FriendRequestCreate(BaseModel):
    username: str


class MessageCreate(BaseModel):
    to: str
    text: str = Field(min_length=1, max_length=1000)


class NowPlayingUpdate(BaseModel):
    to: str
    title: Optional[str] = None
    artist: Optional[str] = None
    position: Optional[float] = None
    is_playing: bool = False
