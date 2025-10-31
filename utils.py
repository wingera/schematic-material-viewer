"""
工具函数模块
"""
import os
import hashlib
import chardet
from typing import Tuple, List, Dict, Any
from config import Config

class FileUtils:
    """文件工具类"""
    
    @staticmethod
    def ensure_directories() -> None:
        """确保必要的目录存在"""
        for folder in [Config.UPLOAD_FOLDER, Config.USERS_FOLDER]:
            if not os.path.exists(folder):
                os.makedirs(folder)
                print(f"创建目录: {folder}")
    
    @staticmethod
    def hash_password(password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def allowed_file(filename: str) -> bool:
        """检查文件类型是否允许"""
        if '.' not in filename:
            return False
        ext = filename.rsplit('.', 1)[1].lower()
        return ext in Config.ALLOWED_EXTENSIONS
    
    @staticmethod
    def secure_filename(filename: str) -> str:
        """安全文件名处理"""
        # 简单的安全文件名处理，实际项目中可以使用werkzeug的secure_filename
        keepchars = (' ', '.', '_', '-')
        return "".join(c for c in filename if c.isalnum() or c in keepchars).rstrip()
    
    @staticmethod
    def get_file_size(filepath: str) -> int:
        """获取文件大小"""
        try:
            return os.path.getsize(filepath)
        except OSError:
            return 0

class CalculationUtils:
    """计算工具类"""
    
    @staticmethod
    def calculate_boxes_and_groups(quantity: str) -> Tuple[int, int, int]:
        """计算盒数、组数和个数"""
        try:
            quantity = int(quantity)
            items_per_group = Config.ITEMS_PER_GROUP
            groups_per_box = Config.GROUPS_PER_BOX
            
            total_boxes = quantity // (items_per_group * groups_per_box)
            total_groups = (quantity // items_per_group) - (total_boxes * groups_per_box)
            pieces = quantity - ((total_boxes * groups_per_box + total_groups) * items_per_group)
            
            return total_boxes, total_groups, pieces
        except (ValueError, TypeError):
            return 0, 0, 0
    
    @staticmethod
    def detect_encoding(filepath: str) -> str:
        """检测文件编码"""
        try:
            with open(filepath, 'rb') as f:
                raw_data = f.read(1024)  # 只读取前1024字节来检测编码
                result = chardet.detect(raw_data)
                return result.get('encoding', 'utf-8')
        except Exception:
            return 'utf-8'

class ValidationUtils:
    """验证工具类"""
    
    @staticmethod
    def validate_username(username: str) -> Tuple[bool, str]:
        """验证用户名"""
        username = username.strip()
        if not username:
            return False, "用户名不能为空"
        if len(username) < 3:
            return False, "用户名至少需要3个字符"
        if len(username) > 20:
            return False, "用户名不能超过20个字符"
        if not username.replace('_', '').isalnum():
            return False, "用户名只能包含字母、数字和下划线"
        return True, "用户名有效"
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """验证密码"""
        if not password:
            return False, "密码不能为空"
        if len(password) < 6:
            return False, "密码至少需要6个字符"
        if len(password) > 50:
            return False, "密码不能超过50个字符"
        return True, "密码有效"
