"""
数据管理模块
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from models import User, FileInfo
from utils import FileUtils, ValidationUtils
from config import Config

logger = logging.getLogger(__name__)

class UserManager:
    """用户管理器"""
    
    def __init__(self):
        self.users_file = f"{Config.USERS_FOLDER}/users.json"
        FileUtils.ensure_directories()
    
    def load_users(self) -> Dict[str, User]:
        """加载所有用户数据"""
        users = {}
        if not FileUtils.get_file_size(self.users_file):
            logger.info("用户文件不存在或为空，创建新文件")
            return users
        
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for username, user_data in data.items():
                users[username] = User(
                    username=username,
                    password_hash=user_data.get('password_hash', ''),
                    created_at=user_data.get('created_at', ''),
                    last_login=user_data.get('last_login')
                )
            
            logger.info(f"成功加载 {len(users)} 个用户")
            return users
            
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"加载用户数据失败: {e}")
            return {}
    
    def save_users(self, users: Dict[str, User]) -> bool:
        """保存用户数据"""
        try:
            # 转换为可序列化的字典
            users_dict = {}
            for username, user in users.items():
                users_dict[username] = {
                    'password_hash': user.password_hash,
                    'created_at': user.created_at,
                    'last_login': user.last_login
                }
            
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存 {len(users)} 个用户数据")
            return True
            
        except IOError as e:
            logger.error(f"保存用户数据失败: {e}")
            return False
    
    def register_user(self, username: str, password: str) -> Tuple[bool, str]:
        """注册新用户"""
        # 验证用户名和密码
        is_valid, message = ValidationUtils.validate_username(username)
        if not is_valid:
            return False, message
        
        is_valid, message = ValidationUtils.validate_password(password)
        if not is_valid:
            return False, message
        
        users = self.load_users()
        
        # 检查用户是否已存在
        if username in users:
            return False, "用户名已存在"
        
        # 创建新用户
        users[username] = User(
            username=username,
            password_hash=FileUtils.hash_password(password),
            created_at=datetime.now().isoformat()
        )
        
        if self.save_users(users):
            logger.info(f"用户注册成功: {username}")
            return True, "注册成功"
        else:
            return False, "注册失败，请重试"
    
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, str]:
        """用户认证"""
        users = self.load_users()
        
        if username not in users:
            return False, "用户名或密码错误"
        
        user = users[username]
        password_hash = FileUtils.hash_password(password)
        
        if user.password_hash == password_hash:
            # 更新最后登录时间
            user.last_login = datetime.now().isoformat()
            self.save_users(users)
            logger.info(f"用户认证成功: {username}")
            return True, "登录成功"
        else:
            return False, "用户名或密码错误"

class FileManager:
    """文件管理器"""
    
    def __init__(self):
        self.files_file = f"{Config.USERS_FOLDER}/files.json"
        FileUtils.ensure_directories()
    
    def load_file_list(self) -> List[FileInfo]:
        """加载文件列表"""
        if not FileUtils.get_file_size(self.files_file):
            return []
        
        try:
            with open(self.files_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            files = []
            for file_data in data:
                files.append(FileInfo(
                    filename=file_data['filename'],
                    owner=file_data['owner'],
                    description=file_data.get('description', ''),
                    created_at=file_data['created_at'],
                    size=file_data.get('size', 0),
                    last_modified=file_data.get('last_modified')
                ))
            
            return files
            
        except (json.JSONDecodeError, IOError, KeyError) as e:
            logger.error(f"加载文件列表失败: {e}")
            return []
    
    def save_file_list(self, files: List[FileInfo]) -> bool:
        """保存文件列表"""
        try:
            # 转换为可序列化的字典列表
            files_data = []
            for file_info in files:
                files_data.append({
                    'filename': file_info.filename,
                    'owner': file_info.owner,
                    'description': file_info.description,
                    'created_at': file_info.created_at,
                    'size': file_info.size,
                    'last_modified': file_info.last_modified
                })
            
            with open(self.files_file, 'w', encoding='utf-8') as f:
                json.dump(files_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except IOError as e:
            logger.error(f"保存文件列表失败: {e}")
            return False
    
    def add_file_to_list(self, filename: str, username: str, description: str = "") -> Optional[FileInfo]:
        """添加文件到列表"""
        files = self.load_file_list()
        file_path = f"{Config.UPLOAD_FOLDER}/{filename}"
        
        file_info = FileInfo(
            filename=filename,
            owner=username,
            description=description,
            created_at=datetime.now().isoformat(),
            size=FileUtils.get_file_size(file_path)
        )
        
        # 检查是否已存在同名文件，如果存在则更新
        existing_index = -1
        for i, f in enumerate(files):
            if f.filename == filename and f.owner == username:
                existing_index = i
                break
        
        if existing_index >= 0:
            files[existing_index] = file_info
        else:
            files.append(file_info)
        
        if self.save_file_list(files):
            return file_info
        return None
    
    def get_user_files(self, username: str) -> List[FileInfo]:
        """获取用户的文件列表"""
        files = self.load_file_list()
        return [f for f in files if f.owner == username]
    
    def delete_file(self, filename: str, username: str) -> Tuple[bool, str]:
        """删除文件"""
        files = self.load_file_list()
        
        # 检查文件所有权
        file_owned = any(f.filename == filename and f.owner == username for f in files)
        if not file_owned:
            return False, "无权删除此文件"
        
        # 从文件列表中移除
        updated_files = [f for f in files if not (f.filename == filename and f.owner == username)]
        
        # 删除物理文件
        file_path = f"{Config.UPLOAD_FOLDER}/{filename}"
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError as e:
            logger.error(f"删除物理文件失败: {e}")
            return False, "删除文件失败"
        
        if self.save_file_list(updated_files):
            logger.info(f"用户 {username} 删除了文件 {filename}")
            return True, f"文件已删除: {filename}"
        else:
            return False, "删除文件失败"
