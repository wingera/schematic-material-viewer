"""
主应用模块 - 原理图材料列表查看器
"""

import os
import json
import logging
import csv
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_socketio import SocketIO, emit
from flask_socketio import SocketIO, emit, join_room

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 获取当前文件所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# 应用配置
class Config:
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(BASE_DIR, 'uploads'))
    USERS_FOLDER = os.environ.get('USERS_FOLDER', os.path.join(BASE_DIR, 'users'))
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    ALLOWED_EXTENSIONS = {'csv', 'sti'}
    ITEMS_PER_GROUP = 64
    GROUPS_PER_BOX = 27

app.config.from_object(Config)

# 配置静态文件路径
app.static_folder = os.path.join(BASE_DIR, 'static')
app.template_folder = os.path.join(BASE_DIR, 'templates')

# 关键修复：正确初始化 Socket.IO
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='eventlet',
                   logger=True,
                   engineio_logger=True,
                   ping_timeout=60,
                   ping_interval=25)
logger.info(f"应用初始化完成")
logger.info(f"静态文件目录: {app.static_folder}")
logger.info(f"模板目录: {app.template_folder}")

# 存储活跃状态
active_files = {}
user_sessions = {}

def require_auth(f):
    """认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': '未登录'}), 401
        return f(*args, **kwargs)
    return decorated_function

# 工具函数
class FileUtils:
    @staticmethod
    def ensure_directories():
        """确保必要的目录存在"""
    for folder in [app.config['UPLOAD_FOLDER'], app.config['USERS_FOLDER']]:
        try:
            os.makedirs(folder, exist_ok=True)
            logger.info(f"检查/创建目录: {folder}")
            
            # 测试写入权限
            test_file = os.path.join(folder, 'test_write_permission.tmp')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                logger.info(f"目录 {folder} 写入权限正常")
            except Exception as e:
                logger.error(f"目录 {folder} 没有写入权限: {e}")
                raise
                
        except Exception as e:
            logger.error(f"无法创建或访问目录 {folder}: {e}")

    @staticmethod
    def allowed_file(filename):
        """检查文件类型是否允许"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

    @staticmethod
    def secure_filename(filename):
        """安全文件名处理"""
        keepchars = (' ', '.', '_', '-')
        return "".join(c for c in filename if c.isalnum() or c in keepchars).rstrip()

    @staticmethod
    def calculate_boxes_and_groups(quantity):
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

# 确保目录存在
FileUtils.ensure_directories()

# 路由定义
@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """健康检查端点"""
    return jsonify({
        'status': 'healthy', 
        'message': '应用运行正常',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

# 静态文件路由
@app.route('/css/<path:filename>')
def serve_css(filename):
    """提供 CSS 文件"""
    return send_from_directory(os.path.join(app.static_folder, 'css'), filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    """提供 JS 文件"""
    return send_from_directory(os.path.join(app.static_folder, 'js'), filename)

@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件服务"""
    return send_from_directory(app.static_folder, filename)

@app.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'success': False, 'message': '用户名和密码不能为空'})
        
        # 简化认证逻辑
        if username == "admin" and password == "password":
            session['username'] = username
            session['logged_in'] = True
            logger.info(f"用户 {username} 登录成功")
            return jsonify({'success': True, 'message': '登录成功', 'username': username})
        else:
            return jsonify({'success': False, 'message': '用户名或密码错误'})
    
    except Exception as e:
        logger.error(f"登录处理失败: {e}")
        return jsonify({'success': False, 'message': '登录时发生错误'}), 500

@app.route('/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'success': False, 'message': '用户名和密码不能为空'})
        
        # 简化注册逻辑
        if len(username) >= 3 and len(password) >= 6:
            session['username'] = username
            session['logged_in'] = True
            logger.info(f"用户 {username} 注册成功")
            return jsonify({'success': True, 'message': '注册成功', 'username': username})
        else:
            return jsonify({'success': False, 'message': '用户名至少3个字符，密码至少6个字符'})
    
    except Exception as e:
        logger.error(f"注册处理失败: {e}")
        return jsonify({'success': False, 'message': '注册时发生错误'}), 500

@app.route('/logout', methods=['POST'])
def logout():
    """用户退出登录"""
    try:
        username = session.get('username')
        session.clear()
        logger.info(f"用户 {username} 退出登录")
        return jsonify({'success': True, 'message': '已退出登录'})
    except Exception as e:
        logger.error(f"退出登录处理失败: {e}")
        return jsonify({'success': False, 'message': '退出登录时发生错误'}), 500

@app.route('/check_auth')
def check_auth():
    """检查认证状态"""
    if session.get('logged_in'):
        return jsonify({'logged_in': True, 'username': session.get('username')})
    return jsonify({'logged_in': False})

@app.route('/file_list')
@require_auth
def get_file_list():
    """获取用户文件列表"""
    try:
        files = []
        upload_folder = app.config['UPLOAD_FOLDER']
        if os.path.exists(upload_folder):
            for filename in os.listdir(upload_folder):
                if filename.endswith(('.csv', '.sti')):
                    filepath = os.path.join(upload_folder, filename)
                    files.append({
                        'filename': filename,
                        'owner': session.get('username'),
                        'description': '',
                        'created_at': datetime.fromtimestamp(os.path.getctime(filepath)).isoformat(),
                        'size': os.path.getsize(filepath)
                    })
        
        return jsonify({'files': files})
    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        return jsonify({'error': '获取文件列表时发生错误'}), 500

@app.route('/all_files')
@require_auth
def get_all_files():
    """获取所有文件列表"""
    try:
        files = []
        upload_folder = app.config['UPLOAD_FOLDER']
        if os.path.exists(upload_folder):
            for filename in os.listdir(upload_folder):
                if filename.endswith(('.csv', '.sti')):
                    filepath = os.path.join(upload_folder, filename)
                    files.append({
                        'filename': filename,
                        'owner': 'system',
                        'description': '',
                        'created_at': datetime.fromtimestamp(os.path.getctime(filepath)).isoformat(),
                        'size': os.path.getsize(filepath)
                    })
        
        return jsonify({'files': files})
    except Exception as e:
        logger.error(f"获取所有文件列表失败: {e}")
        return jsonify({'error': '获取文件列表时发生错误'}), 500

@app.route('/upload', methods=['POST'])
@require_auth
def upload_file():
    """上传文件"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有选择文件'}), 400
        
        file = request.files['file']
        description = request.form.get('description', '').strip()
        
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        if not FileUtils.allowed_file(file.filename):
            return jsonify({'error': '不支持的文件类型'}), 400
        
        filename = FileUtils.secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # 确保上传目录存在
        try:
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        except Exception as e:
            logger.error(f"无法创建上传目录: {e}")
            return jsonify({'error': f'无法创建上传目录: {str(e)}'}), 500
        
        # 检查目录写入权限
        if not os.access(app.config['UPLOAD_FOLDER'], os.W_OK):
            logger.error(f"上传目录没有写入权限: {app.config['UPLOAD_FOLDER']}")
            return jsonify({'error': '服务器配置错误：上传目录没有写入权限'}), 500
        
        # 保存文件
        try:
            file.save(filepath)
            logger.info(f"文件保存成功: {filepath}")
        except Exception as e:
            logger.error(f"文件保存失败: {e}")
            return jsonify({'error': f'文件保存失败: {str(e)}'}), 500
        
        # 解析文件逻辑
        data = []
        if filename.endswith('.sti'):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                # 删除无效文件
                try:
                    os.remove(filepath)
                except:
                    pass
                return jsonify({'error': f'STI文件解析失败: {str(e)}'}), 400
        else:
            # CSV 解析逻辑 - 支持JSON格式的CSV文件
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content.startswith('[') and content.endswith(']'):
                        # 如果是JSON格式，直接解析
                        data = json.loads(content)
                    else:
                        # 否则按标准CSV格式解析
                        f.seek(0)  # 重置文件指针
                        reader = csv.reader(f)
                        header = next(reader, None)
                        for row_num, row in enumerate(reader, start=2):
                            if len(row) >= 2:
                                item_name = row[0].strip()
                                quantity_str = row[1].strip()
                                
                                if item_name and quantity_str:
                                    boxes, groups, pieces = FileUtils.calculate_boxes_and_groups(quantity_str)
                                    data.append([item_name, quantity_str, boxes, groups, pieces, "未完成"])
            except Exception as e:
                # 删除无效文件
                try:
                    os.remove(filepath)
                except:
                    pass
                return jsonify({'error': f'CSV文件解析失败: {str(e)}'}), 400
        
        return jsonify({
            'success': True,
            'filename': filename,
            'data': data,
            'file_info': {
                'filename': filename,
                'owner': session.get('username'),
                'description': description,
                'created_at': datetime.now().isoformat(),
                'size': os.path.getsize(filepath)
            }
        })
    
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        return jsonify({'error': f'文件上传时发生错误: {str(e)}'}), 500

@app.route('/save', methods=['POST'])
@require_auth
def save_file():
    """保存文件"""
    try:
        data = request.get_json()
        file_data = data.get('data')
        filename = data.get('filename', 'materials.sti')
        description = data.get('description', '')
        
        if not filename:
            return jsonify({'error': '文件名不能为空'}), 400
        
        if not filename.endswith('.sti'):
            filename += '.sti'
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], FileUtils.secure_filename(filename))
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(file_data, f, ensure_ascii=False, indent=4)
        
        return jsonify({
            'message': f'文件成功保存: {filename}',
            'file_info': {
                'filename': filename,
                'owner': session.get('username'),
                'description': description,
                'created_at': datetime.now().isoformat(),
                'size': os.path.getsize(filepath)
            }
        })
    
    except Exception as e:
        logger.error(f"文件保存失败: {e}")
        return jsonify({'error': f'保存文件时出错: {e}'}), 500

@app.route('/open_file/<filename>')
@require_auth
def open_file(filename):
    """打开文件"""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], FileUtils.secure_filename(filename))
        
        if not os.path.exists(filepath):
            return jsonify({'error': '文件不存在'}), 404
        
        if filename.endswith('.sti'):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            # 对于CSV文件，重新解析
            data = []
            with open(filepath, 'r', encoding='utf-8') as f:
                # 检查文件内容是否为JSON格式
                content = f.read().strip()
                if content.startswith('[') and content.endswith(']'):
                    # 如果是JSON格式，直接解析
                    data = json.loads(content)
                else:
                    # 否则按标准CSV格式解析
                    f.seek(0)  # 重置文件指针
                    reader = csv.reader(f)
                    header = next(reader, None)
                    for row in reader:
                        if len(row) >= 2:
                            item_name = row[0].strip()
                            quantity_str = row[1].strip()
                            if item_name and quantity_str:
                                boxes, groups, pieces = FileUtils.calculate_boxes_and_groups(quantity_str)
                                data.append([item_name, quantity_str, boxes, groups, pieces, "未完成"])
        
        return jsonify({
            'filename': filename,
            'data': data
        })
    
    except Exception as e:
        logger.error(f"打开文件失败: {e}")
        return jsonify({'error': f'读取文件时出错: {e}'}), 500
    
    except Exception as e:
        logger.error(f"打开文件失败: {e}")
        return jsonify({'error': f'读取文件时出错: {e}'}), 500

@app.route('/delete_file/<filename>', methods=['DELETE'])
@require_auth
def delete_file(filename):
    """删除文件"""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], FileUtils.secure_filename(filename))
        
        if not os.path.exists(filepath):
            return jsonify({'error': '文件不存在'}), 404
        
        os.remove(filepath)
        logger.info(f"用户 {session.get('username')} 删除了文件 {filename}")
        
        return jsonify({'message': f'文件已删除: {filename}'})
    
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        return jsonify({'error': f'删除文件时出错: {e}'}), 500

@app.route('/auto_save', methods=['POST'])
@require_auth
def auto_save():
    """自动保存文件"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        file_data = data.get('data')
        
        if not filename or not file_data:
            return jsonify({'error': '缺少必要参数'}), 400
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], FileUtils.secure_filename(filename))
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(file_data, f, ensure_ascii=False, indent=4)
        
        return jsonify({'success': True, 'message': '自动保存成功'})
    
    except Exception as e:
        logger.error(f"自动保存失败: {e}")
        return jsonify({'error': f'自动保存时出错: {e}'}), 500

@app.after_request
def after_request(response):
    """添加响应头"""
    # 设置正确的 MIME 类型
    if response.content_type == 'text/html':
        if request.path.endswith('.css'):
            response.content_type = 'text/css'
        elif request.path.endswith('.js'):
            response.content_type = 'application/javascript'
    
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

# Socket.IO 事件处理
@socketio.on('connect')
def handle_connect():
    """处理客户端连接"""
    logger.info(f"客户端连接: {request.sid}")
    user_sessions[request.sid] = {
        'sid': request.sid,
        'username': '未登录用户',
        'joined_at': datetime.now().isoformat(),
        'current_file': None
    }
    emit('connection_established', {
        'message': '连接成功', 
        'userCount': len(user_sessions),
        'sid': request.sid
    })

@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开连接"""
    sid = request.sid
    if sid in user_sessions:
        username = user_sessions[sid]['username']
        current_file = user_sessions[sid].get('current_file')
        
        # 从文件用户列表中移除
        if current_file and current_file in active_files:
            active_files[current_file]['users'] = [
                user for user in active_files[current_file]['users'] 
                if user['sid'] != sid
            ]
            
            # 如果文件没有用户了，清理文件数据
            if not active_files[current_file]['users']:
                del active_files[current_file]
            else:
                # 广播用户离开事件
                emit('user_left', {
                    'username': username,
                    'userCount': len(active_files[current_file]['users'])
                }, room=current_file)
        
        del user_sessions[sid]
        logger.info(f"客户端断开: {sid}, 用户: {username}")


@socketio.on('join_file')
def handle_join_file(data):
    """处理加入文件编辑"""
    filename = data.get('filename')
    username = data.get('username', '未登录用户')
    
    logger.info(f"用户 {username} 请求加入文件 {filename}")
    
    # 更新用户会话
    if request.sid in user_sessions:
        user_sessions[request.sid]['current_file'] = filename
        user_sessions[request.sid]['username'] = username
    
    # 初始化文件数据
    if filename not in active_files:
        active_files[filename] = {
            'data': [],
            'users': []
        }
    
    # 添加用户到文件（确保不重复）
    existing_user = next((u for u in active_files[filename]['users'] if u['sid'] == request.sid), None)
    if not existing_user:
        active_files[filename]['users'].append({
            'sid': request.sid,
            'username': username
        })
    
    # 将用户加入房间
    join_room(filename)
    
    logger.info(f"用户 {username} 加入了文件 {filename}, 当前用户数: {len(active_files[filename]['users'])}")
    
    # 发送当前文件数据（如果有）
    if active_files[filename]['data']:
        emit('file_data', {
            'filename': filename,
            'data': active_files[filename]['data']
        }, room=request.sid)
    
    # 广播用户加入事件给房间内所有用户
    emit('user_joined', {
        'username': username,
        'userCount': len(active_files[filename]['users']),
        'users': [u['username'] for u in active_files[filename]['users']]
    }, room=filename)

@socketio.on('file_loaded')
def handle_file_loaded(data):
    """处理文件加载完成"""
    filename = data.get('filename')
    file_data = data.get('data', [])
    
    logger.info(f"文件 {filename} 数据已加载，共{len(file_data)}项")
    
    if filename not in active_files:
        active_files[filename] = {
            'data': [],
            'users': []
        }
    
    active_files[filename]['data'] = file_data

@socketio.on('item_updated')
def handle_item_updated(data):
    """处理项目更新"""
    filename = data.get('filename')
    row_index = data.get('rowIndex')
    new_status = data.get('status')
    username = data.get('username', '未知用户')
    
    logger.info(f"收到项目更新: 文件 {filename}, 行 {row_index}, 状态 {new_status}, 用户 {username}")
    
    if filename in active_files and 0 <= row_index < len(active_files[filename]['data']):
        # 更新服务器端数据
        active_files[filename]['data'][row_index][5] = new_status
        
        # 广播更新给所有在同一个文件的用户（不包括发送者）
        emit('item_updated', {
            'rowIndex': row_index,
            'status': new_status,
            'filename': filename,
            'username': username
        }, room=filename, include_self=False)
        
        logger.info(f"广播更新: 文件 {filename} 第{row_index}行状态更新为: {new_status}, 由用户 {username} 修改")
    else:
        logger.warning(f"无法更新项目: 文件 {filename} 不存在或行索引 {row_index} 无效")

@socketio.on('sync_file_data')
def handle_sync_file_data(data):
    """同步文件数据"""
    filename = data.get('filename')
    file_data = data.get('data', [])
    
    logger.info(f"收到文件数据同步: 文件 {filename}, 数据长度 {len(file_data)}")
    
    if filename not in active_files:
        active_files[filename] = {
            'data': [],
            'users': []
        }
    
    # 更新服务器端数据
    active_files[filename]['data'] = file_data
    
    # 广播给房间内其他用户
    emit('file_data_updated', {
        'filename': filename,
        'data': file_data
    }, room=filename, include_self=False)

# 添加 Socket.IO 测试路由
@app.route('/socketio-test')
def socketio_test():
    """Socket.IO 测试路由"""
    return jsonify({'message': 'Socket.IO 路由正常'})

if __name__ == '__main__':
    logger.info("原理图材料列表查看器启动中...")
    logger.info(f"环境: {os.environ.get('FLASK_ENV', 'development')}")
    logger.info(f"上传目录: {app.config['UPLOAD_FOLDER']}")
    logger.info(f"用户目录: {app.config['USERS_FOLDER']}")
    
    # 检查上传目录权限
    upload_dir = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_dir):
        try:
            os.makedirs(upload_dir, exist_ok=True)
            logger.info(f"创建上传目录: {upload_dir}")
        except Exception as e:
            logger.error(f"无法创建上传目录: {e}")
    
    if os.path.exists(upload_dir):
        test_file = os.path.join(upload_dir, 'test_permission.tmp')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            logger.info("上传目录权限检查通过")
        except Exception as e:
            logger.error(f"上传目录没有写入权限: {e}")
    
    # 移除不支持的参数
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    socketio.run(app, 
                host=os.environ.get('HOST', '0.0.0.0'), 
                port=int(os.environ.get('PORT', 5000)), 
                debug=debug_mode)
