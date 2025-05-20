from dataclasses import dataclass
from typing import List, Optional

@dataclass
class User:
    id: int
    id_str: str
    name: str
    screen_name: str
    location: str
    description: str
    protected: bool
    followers_count: int
    friends_count: int
    listed_count: int
    created_ts: int
    favourites_count: int
    verified: bool
    statuses_count: int
    media_count: int
    profile_background_image_url_https: str
    profile_image_url_https: str
    profile_banner_url: str
    is_blue_verified: bool
    verified_type: str
    pin_tweet_id: str
    ca: str
    has_ca: bool
    init_followers_count: int
    init_friends_count: int
    first_created_at: int
    updated_at: int

@dataclass
class Tweet:
    id: int
    tweet_id: str
    user_id: str
    media_type: str
    text: str
    medias: List[str]
    urls: Optional[any]
    is_self_send: bool
    is_retweet: bool
    is_quote: bool
    is_reply: bool
    is_like: bool
    related_tweet_id: str
    related_user_id: str
    publish_time: int
    has_deleted: bool
    last_deleted_check_at: int
    ca: str
    has_ca: bool
    created_at: int
    updated_at: int

@dataclass
class PushMsg:
    push_type: str
    title: str
    content: str
    user: User
    tweet: Optional[Tweet] = None


@dataclass
class Msg:
    push_type: str
    title: str
    content: str
    name: str
    screen_name: str
