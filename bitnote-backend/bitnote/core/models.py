from sqlalchemy import Column, String, Integer, Text, ForeignKey
from database import Base


class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password_hash = Column(String)


class Notebook(Base):
    __tablename__ = "notebooks"
    notebook_id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    title = Column(String)
    notebook_type = Column(String)
    description = Column(String)
    created_at = Column(Integer)


class Cell(Base):
    __tablename__ = "cells"
    cell_id = Column(String, primary_key=True)
    notebook_id = Column(String, ForeignKey("notebooks.notebook_id"))
    order_index = Column(Integer)
    cell_type = Column(String)
    user_content = Column(Text)
    ai_content = Column(Text)


class EducationalMetadata(Base):
    __tablename__ = "educational_metadata"

    edu_id = Column(Integer, primary_key=True)
    notebook_id = Column(String)
    learning_goal = Column(String)
    syllabus = Column(Text)
    roadmap = Column(Text)
    progress = Column(float, default=0.0)
