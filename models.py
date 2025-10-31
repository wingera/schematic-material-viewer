"""
数据模型模块
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class User:
    """用户模型"""
    username: str
    password_hash: str
    created_at: str
    last_login: Optional[str] = None

@dataclass
class FileInfo:
    """文件信息模型"""
    filename: str
    owner: str
    description: str
    created_at: str
    size: int
    last_modified: Optional[str] = None

@dataclass
class MaterialItem:
    """材料项模型"""
    name: str
    quantity: int
    boxes: int
    groups: int
    pieces: int
    status: str  # 'completed', 'in-progress', 'not-completed'

@dataclass
class SessionData:
    """会话数据模型"""
    sid: str
    username: str
    current_file: Optional[str] = None
    joined_at: Optional[str] = None

@dataclass
class ActiveFile:
    """活跃文件模型"""
    filename: str
    data: List[MaterialItem]
    users: List[SessionData]
    last_activity: str



