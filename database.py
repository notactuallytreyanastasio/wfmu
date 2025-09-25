from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, ForeignKey, Table, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json

Base = declarative_base()

post_categories = Table('post_categories', Base.metadata,
    Column('post_id', String, ForeignKey('posts.post_id')),
    Column('category_id', Integer, ForeignKey('categories.id'))
)

class Post(Base):
    __tablename__ = 'posts'

    post_id = Column(String, primary_key=True)
    url = Column(String, unique=True, nullable=False)
    title = Column(Text)
    author = Column(String)
    published_date = Column(DateTime)
    raw_html = Column(Text)
    content_text = Column(Text)
    content_markdown = Column(Text)
    scraped_at = Column(DateTime, default=datetime.utcnow)

    categories = relationship('Category', secondary=post_categories, back_populates='posts')
    media_items = relationship('Media', back_populates='post')
    comments = relationship('Comment', back_populates='post')

class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    url = Column(String)
    post_count = Column(Integer)

    posts = relationship('Post', secondary=post_categories, back_populates='categories')

class Media(Base):
    __tablename__ = 'media'

    id = Column(Integer, primary_key=True)
    post_id = Column(String, ForeignKey('posts.post_id'))
    media_type = Column(String)
    original_url = Column(String)
    local_path = Column(String)
    filename = Column(String)
    alt_text = Column(Text)
    caption = Column(Text)
    downloaded = Column(Boolean, default=False)
    download_error = Column(Text)

    post = relationship('Post', back_populates='media_items')

class Comment(Base):
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True)
    post_id = Column(String, ForeignKey('posts.post_id'))
    author = Column(String)
    date = Column(DateTime)
    content = Column(Text)

    post = relationship('Post', back_populates='comments')

class ScrapeProgress(Base):
    __tablename__ = 'scrape_progress'

    id = Column(Integer, primary_key=True)
    page_type = Column(String)
    url = Column(String, unique=True)
    scraped = Column(Boolean, default=False)
    error = Column(Text)
    last_attempt = Column(DateTime)

def init_database(db_path='wfmu_archive.db'):
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session(), engine