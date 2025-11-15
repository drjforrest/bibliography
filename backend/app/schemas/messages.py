from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class MessageTopicBase(BaseModel):
    """Base schema for message topic data."""

    name: str = Field(..., min_length=1, max_length=100)
    icon: Optional[str] = Field(default="chat", max_length=50)
    description: Optional[str] = None


class MessageTopicCreate(MessageTopicBase):
    """Schema for creating a new message topic."""

    pass


class MessageTopicUpdate(BaseModel):
    """Schema for updating a message topic."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    icon: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None


class MessageTopicResponse(MessageTopicBase):
    """Response schema for message topic data."""

    id: int
    user_id: str
    created_at: datetime
    unread_count: Optional[int] = 0
    last_message: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageTopicListResponse(BaseModel):
    """Response schema for topic lists."""

    topics: List[MessageTopicResponse]
    total: int


class MessageBase(BaseModel):
    """Base schema for message data."""

    content: str = Field(..., min_length=1)
    topic_id: int
    parent_id: Optional[int] = None


class MessageCreate(BaseModel):
    """Schema for creating a new message."""

    content: str = Field(..., min_length=1)
    topic_id: int
    parent_id: Optional[int] = None


class MessageUpdate(BaseModel):
    """Schema for updating a message."""

    content: Optional[str] = Field(None, min_length=1)


class UserInfo(BaseModel):
    """Simple user info for message responses."""

    id: str
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Response schema for message data."""

    id: int
    content: str
    topic_id: int
    user_id: str
    user: UserInfo
    created_at: datetime
    parent_id: Optional[int] = None

    class Config:
        from_attributes = True


class MessageWithReplies(MessageResponse):
    """Response schema for message with its replies."""

    replies: List["MessageWithReplies"] = []

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """Response schema for message lists."""

    messages: List[MessageResponse]
    total: int


# Allow forward references for recursive model
MessageWithReplies.model_rebuild()
