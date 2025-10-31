/**
 * 原理图材料列表查看器 - 增强版
 * 重新启用 Socket.IO 功能
 */

// 配置常量
const CONFIG = {
    AUTO_SAVE_INTERVAL: 30000,
    DOUBLE_CLICK_DELAY: 500,
    MIN_TOUCH_TARGET: 44,
    NOTIFICATION_DURATION: 5000
};

// 全局状态管理
const AppState = {
    currentData: [],
    currentFilename: '',
    selectedRow: null,
    socket: null,
    currentUser: null,
    autoSaveInterval: null,
    lastSavedData: null,
    mobileSelectedRow: null,
    isIOS: /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream,
    isMobile: /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
};

// DOM 元素缓存 - 在 DOM 加载完成后初始化
let DOM = {};

// 工具函数
const Utils = {
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    checkConnection() {
        return AppState.socket && AppState.socket.connected;
    },

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    },

    showNotification(message, type = 'info') {
    // 移除现有通知
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-message">${message}</span>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // 显示动画
    setTimeout(() => notification.classList.add('show'), 100);
    
    // 自动隐藏
    if (type !== 'error') { // 错误通知不自动隐藏
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
},

    showLoading(button, text = '处理中...') {
        const originalText = button.innerHTML;
        button.innerHTML = `
            <span class="spinner"></span>
            <span>${text}</span>
        `;
        button.disabled = true;
        
        return () => {
            button.innerHTML = originalText;
            button.disabled = false;
        };
    },

    // 安全的 DOM 元素获取
    getElement(id) {
        const element = document.getElementById(id);
        if (!element) {
            console.warn(`Element with id '${id}' not found`);
        }
        return element;
    }

    

};

// 核心应用类
class MaterialsApp {
    constructor() {
        this.init();
    }

    async init() {
        // 等待 DOM 加载完成
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.initializeApp();
            });
        } else {
            this.initializeApp();
        }
    }

    initializeApp() {
        // 初始化 DOM 元素缓存
        this.initializeDOM();
        
        // 检查认证状态
        this.checkAuthStatus();
        this.setupEventListeners();
        this.setupAutoSave();
        this.setupMobileFeatures();
        this.setupContextMenu();
    }

    initializeDOM() {
        // 安全地初始化 DOM 元素缓存
        DOM = {
            authContainer: Utils.getElement('authContainer'),
            appContainer: Utils.getElement('appContainer'),
            fileInput: Utils.getElement('fileInput'),
            tableBody: Utils.getElement('tableBody'),
            statsBar: Utils.getElement('statsBar'),
            totalItems: Utils.getElement('totalItems'),
            completedItems: Utils.getElement('completedItems'),
            inProgressItems: Utils.getElement('inProgressItems'),
            notCompletedItems: Utils.getElement('notCompletedItems'),
            fileList: Utils.getElement('fileList'),
            currentUsername: Utils.getElement('currentUsername'),
            mobileToolbar: Utils.getElement('mobileToolbar'),
            loginForm: Utils.getElement('loginForm'),
            registerForm: Utils.getElement('registerForm'),
            loginTab: Utils.getElement('loginTab'),
            registerTab: Utils.getElement('registerTab'),
            logoutBtn: Utils.getElement('logoutBtn'),
            openFileBtn: Utils.getElement('openFileBtn'),
            saveFileBtn: Utils.getElement('saveFileBtn'),
            refreshFilesBtn: Utils.getElement('refreshFilesBtn'),
            showAllFilesBtn: Utils.getElement('showAllFilesBtn'),
            connectionDot: Utils.getElement('connectionDot'),
            connectionStatus: Utils.getElement('connectionStatus'),
            mobileInProgressBtn: Utils.getElement('mobileInProgressBtn'),
            mobileCompletedBtn: Utils.getElement('mobileCompletedBtn'),
            mobileNotCompletedBtn: Utils.getElement('mobileNotCompletedBtn'),
            mobileCancelBtn: Utils.getElement('mobileCancelBtn')
        };

        // 检查必要的 DOM 元素
        if (!DOM.authContainer || !DOM.appContainer) {
            console.error('必要的 DOM 元素未找到，应用无法正常启动');
            return;
        }
    }

    async checkAuthStatus() {
        try {
            const response = await fetch('/check_auth');
            const data = await response.json();
            
            if (data.logged_in) {
                AppState.currentUser = data.username;
                this.showAppInterface();
            } else {
                this.showAuthInterface();
            }
        } catch (error) {
            console.error('检查认证状态时出错:', error);
            this.showAuthInterface();
        }
    }

    showAuthInterface() {
        if (DOM.authContainer) DOM.authContainer.style.display = 'block';
        if (DOM.appContainer) DOM.appContainer.style.display = 'none';
    }

    showAppInterface() {
    if (DOM.authContainer) DOM.authContainer.style.display = 'none';
    if (DOM.appContainer) DOM.appContainer.style.display = 'block';
    
    if (DOM.currentUsername) {
        DOM.currentUsername.textContent = AppState.currentUser || '用户';
    }
    
    // 初始化 Socket.IO
    this.initializeSocket();
    
    // 加载文件列表和恢复会话
    this.loadFileList();
    this.restoreLastSession();
}

    setupEventListeners() {
        // 安全地添加事件监听器
        if (DOM.loginTab) {
            DOM.loginTab.addEventListener('click', () => this.switchAuthTab('login'));
        }
        if (DOM.registerTab) {
            DOM.registerTab.addEventListener('click', () => this.switchAuthTab('register'));
        }
        if (DOM.loginForm) {
            DOM.loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }
        if (DOM.registerForm) {
            DOM.registerForm.addEventListener('submit', (e) => this.handleRegister(e));
        }
        if (DOM.logoutBtn) {
            DOM.logoutBtn.addEventListener('click', () => this.handleLogout());
        }
        if (DOM.openFileBtn) {
            DOM.openFileBtn.addEventListener('click', () => DOM.fileInput?.click());
        }
        if (DOM.saveFileBtn) {
            DOM.saveFileBtn.addEventListener('click', () => this.saveFile());
        }
        if (DOM.refreshFilesBtn) {
            DOM.refreshFilesBtn.addEventListener('click', () => this.loadFileList());
        }
        if (DOM.showAllFilesBtn) {
            DOM.showAllFilesBtn.addEventListener('click', () => this.loadAllFiles());
        }
        if (DOM.fileInput) {
            DOM.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }
        
        // 移动端事件
        this.setupMobileEventListeners();
    }

    switchAuthTab(tab) {
        if (tab === 'login') {
            if (DOM.loginTab) DOM.loginTab.classList.add('active');
            if (DOM.registerTab) DOM.registerTab.classList.remove('active');
            if (DOM.loginForm) DOM.loginForm.style.display = 'block';
            if (DOM.registerForm) DOM.registerForm.style.display = 'none';
        } else {
            if (DOM.loginTab) DOM.loginTab.classList.remove('active');
            if (DOM.registerTab) DOM.registerTab.classList.add('active');
            if (DOM.loginForm) DOM.loginForm.style.display = 'none';
            if (DOM.registerForm) DOM.registerForm.style.display = 'block';
        }
    }

    async handleLogin(event) {
        event.preventDefault();
        
        const username = Utils.getElement('loginUsername')?.value;
        const password = Utils.getElement('loginPassword')?.value;
        
        if (!username || !password) {
            Utils.showNotification('❌ 请输入用户名和密码', 'error');
            return;
        }
        
        const disableLoading = Utils.showLoading(event.target, '登录中...');
        
        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (data.success) {
                AppState.currentUser = data.username;
                this.showAppInterface();
                Utils.showNotification(`✅ ${data.message}`, 'success');
            } else {
                Utils.showNotification(`❌ ${data.message}`, 'error');
            }
        } catch (error) {
            console.error('登录失败:', error);
            Utils.showNotification('❌ 登录时发生错误', 'error');
        } finally {
            disableLoading();
        }
    }

    async handleRegister(event) {
        event.preventDefault();
        
        const username = Utils.getElement('registerUsername')?.value;
        const password = Utils.getElement('registerPassword')?.value;
        
        if (!username || !password) {
            Utils.showNotification('❌ 请输入用户名和密码', 'error');
            return;
        }
        
        const disableLoading = Utils.showLoading(event.target, '注册中...');
        
        try {
            const response = await fetch('/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (data.success) {
                AppState.currentUser = data.username;
                this.showAppInterface();
                Utils.showNotification(`✅ ${data.message}`, 'success');
            } else {
                Utils.showNotification(`❌ ${data.message}`, 'error');
            }
        } catch (error) {
            console.error('注册失败:', error);
            Utils.showNotification('❌ 注册时发生错误', 'error');
        } finally {
            disableLoading();
        }
    }

    async handleLogout() {
        try {
            const response = await fetch('/logout', { method: 'POST' });
            const data = await response.json();
            
            if (data.success) {
                AppState.currentUser = null;
                AppState.currentData = [];
                AppState.currentFilename = '';
                
                if (AppState.socket) {
                    AppState.socket.disconnect();
                }
                
                this.showAuthInterface();
                Utils.showNotification('✅ 已退出登录', 'success');
            }
        } catch (error) {
            console.error('退出登录失败:', error);
            Utils.showNotification('❌ 退出登录时发生错误', 'error');
        }
    }

    async handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    // 验证文件类型
    const allowedTypes = ['.csv', '.sti', 'text/csv', 'application/octet-stream'];
    const fileExtension = file.name.toLowerCase().slice(-4);
    
    if (!allowedTypes.includes(fileExtension) && !allowedTypes.includes(file.type)) {
        Utils.showNotification('请选择 CSV 或 STI 格式的文件', 'error');
        event.target.value = '';
        return;
    }

    // 文件大小限制 (10MB)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
        Utils.showNotification('文件大小不能超过 10MB', 'error');
        event.target.value = '';
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        Utils.showNotification('正在上传文件...', 'info');
        
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || data.message || `上传失败: ${response.status}`);
        }

        // 检查服务器返回的数据结构
        if (data.success && data.filename) {
            Utils.showNotification('文件上传成功', 'success');
            
            // 更新文件列表
            await this.loadFileList();
            
            // 如果上传的是当前打开的文件类型，自动打开
            if (data.filename) {
                setTimeout(() => {
                    this.openExistingFile(data.filename);
                }, 1000);
            }
        } else {
            throw new Error(data.error || data.message || '上传失败');
        }

    } catch (error) {
        console.error('上传错误:', error);
        
        let errorMessage = '上传失败';
        if (error.message.includes('413')) {
            errorMessage = '文件太大，请选择小于10MB的文件';
        } else if (error.message.includes('415')) {
            errorMessage = '不支持的文件格式';
        } else if (error.message.includes('500')) {
            if (error.message.includes('Permission denied')) {
                errorMessage = '服务器配置错误：没有文件写入权限，请联系管理员';
            } else if (error.message.includes('无法创建上传目录')) {
                errorMessage = '服务器配置错误：无法创建上传目录，请联系管理员';
            } else {
                errorMessage = '服务器处理文件时出错，请检查文件格式';
            }
        } else {
            errorMessage = error.message;
        }
        
        Utils.showNotification(errorMessage, 'error');
    } finally {
        // 清空文件输入，允许重复选择同一文件
        event.target.value = '';
    }
}

async restoreLastSession() {
    try {
        const lastFile = localStorage.getItem('lastOpenedFile');
        if (lastFile) {
            console.log(`恢复上次会话，尝试打开文件: ${lastFile}`);
            
            // 先检查文件列表，确保文件存在
            const filesResponse = await fetch('/file_list');
            if (filesResponse.ok) {
                const filesData = await filesResponse.json();
                const fileExists = filesData.files && 
                    filesData.files.some(file => file.filename === lastFile);
                
                if (fileExists) {
                    await this.openExistingFile(lastFile); // 修复：使用 this.openExistingFile
                } else {
                    console.log('上次打开的文件已不存在');
                    localStorage.removeItem('lastOpenedFile');
                }
            }
        }
    } catch (error) {
        console.error('恢复会话错误:', error);
        localStorage.removeItem('lastOpenedFile');
    }
}

    renderTable() {
    if (!DOM.tableBody) return;
    
    if (AppState.currentData.length === 0) {
        DOM.tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="empty-state">
                    <div class="icon">📊</div>
                    <div>暂无数据，请上传文件开始使用</div>
                </td>
            </tr>
        `;
        return;
    }

    DOM.tableBody.innerHTML = AppState.currentData.map((row, index) => {
        const status = row[5];
        const statusConfig = this.getStatusConfig(status);
        const isSelected = index === AppState.selectedRow;
        
        return `
            <tr class="${statusConfig.className} ${isSelected ? 'selected-row' : ''}" data-index="${index}">
                ${row.map((cell, cellIndex) => 
                    `<td>${cellIndex === 5 ? this.formatStatusCell(cell, statusConfig.emoji) : cell}</td>`
                ).join('')}
            </tr>
        `;
    }).join('');

    this.attachTableEventListeners();
}

    getStatusConfig(status) {
        const configs = {
            '已完成': { className: 'completed-row', emoji: '🟢' },
            '进行中': { className: 'in-progress-row', emoji: '🟡' },
            '未完成': { className: 'not-completed-row', emoji: '🔴' }
        };
        return configs[status] || configs['未完成'];
    }

    formatStatusCell(cell, emoji) {
        if (AppState.isMobile) {
            return `<span class="mobile-status-indicator"></span><span>${cell}</span>`;
        }
        return `${emoji} ${cell}`;
    }

    attachTableEventListeners() {
    if (!DOM.tableBody) return;
    
    const rows = DOM.tableBody.querySelectorAll('tr');
    rows.forEach(row => {
        if (!AppState.isMobile) {
            // 桌面端右键菜单
            row.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                AppState.selectedRow = parseInt(row.dataset.index);
                this.showContextMenu(e);
            });
            
            // 桌面端左键点击也可以选中行（可选功能）
            row.addEventListener('click', (e) => {
                if (!e.ctrlKey && !e.metaKey) {
                    // 清除其他行的选中状态
                    rows.forEach(r => r.classList.remove('selected-row'));
                }
                row.classList.add('selected-row');
                AppState.selectedRow = parseInt(row.dataset.index);
            });
        } else {
            // 移动端点击事件
            row.addEventListener('click', (e) => {
                AppState.mobileSelectedRow = parseInt(row.dataset.index);
                this.showMobileStatusModal();
            });
        }
    });
}

    showContextMenu(e) {
    e.preventDefault();
    
    const contextMenu = document.getElementById('contextMenu');
    if (!contextMenu) return;
    
    // 设置菜单位置
    const x = e.clientX;
    const y = e.clientY;
    
    contextMenu.style.left = x + 'px';
    contextMenu.style.top = y + 'px';
    contextMenu.style.display = 'block';
    
    // 添加全局点击事件来关闭菜单
    this.hideContextMenuHandler = () => this.hideContextMenu();
    document.addEventListener('click', this.hideContextMenuHandler);
    
    // 阻止右键菜单的默认行为
    e.stopPropagation();
}

hideContextMenu() {
    const contextMenu = document.getElementById('contextMenu');
    if (contextMenu) {
        contextMenu.style.display = 'none';
    }
    
    // 移除全局点击事件
    if (this.hideContextMenuHandler) {
        document.removeEventListener('click', this.hideContextMenuHandler);
        this.hideContextMenuHandler = null;
    }
}

setupContextMenu() {
    const contextMenu = document.getElementById('contextMenu');
    if (!contextMenu) return;
    
    // 为每个菜单项添加点击事件
    const menuItems = contextMenu.querySelectorAll('.context-menu-item');
    menuItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.stopPropagation();
            const action = item.getAttribute('data-action');
            this.handleContextMenuAction(action);
            this.hideContextMenu();
        });
    });
    
    // 阻止在菜单内部点击时触发隐藏
    contextMenu.addEventListener('click', (e) => {
        e.stopPropagation();
    });
}

handleContextMenuAction(action) {
    if (AppState.selectedRow === null || AppState.selectedRow === undefined) {
        Utils.showNotification('❌ 请先选择一行数据', 'error');
        return;
    }
    
    const statusMap = {
        'in-progress': '进行中',
        'completed': '已完成',
        'not-completed': '未完成'
    };
    
    const newStatus = statusMap[action];
    if (newStatus) {
        this.changeStatus(AppState.selectedRow, newStatus);
    }
}

    showMobileStatusModal() {
        if (AppState.isMobile && DOM.mobileToolbar) {
            DOM.mobileToolbar.style.display = 'flex';
        }
    }

    changeStatus(rowIndex, status) {
    if (rowIndex === null || rowIndex === undefined) return;
    
    const statusMap = {
        'completed': '已完成',
        'in-progress': '进行中',
        'not-completed': '未完成'
    };
    
    const newStatus = statusMap[status] || status;
    
    if (!['已完成', '进行中', '未完成'].includes(newStatus)) {
        Utils.showNotification('❌ 无效的状态值', 'error');
        return;
    }
    
    // 保存旧状态用于比较
    const oldStatus = AppState.currentData[rowIndex][5];
    
    // 更新数据
    AppState.currentData[rowIndex][5] = newStatus;
    
    // 更新UI
    this.renderTable();
    this.updateStats();
    
    // 发送Socket通知 - 只有在状态真正改变时发送
    if (AppState.socket && AppState.socket.connected && AppState.currentFilename && oldStatus !== newStatus) {
        AppState.socket.emit('item_updated', {
            filename: AppState.currentFilename,
            rowIndex: rowIndex,
            status: newStatus,
            username: AppState.currentUser
        });
        console.log(`发送状态更新: 文件 ${AppState.currentFilename}, 行 ${rowIndex}, 状态 ${newStatus}`);
    }
    
    // 移动端振动反馈
    if (AppState.isMobile && navigator.vibrate) {
        navigator.vibrate(50);
    }
    
    // 隐藏移动端工具栏
    if (DOM.mobileToolbar && DOM.mobileToolbar.style.display !== 'none') {
        DOM.mobileToolbar.style.display = 'none';
    }
    
    Utils.showNotification(`✅ 已更新状态为: ${newStatus}`, 'success');
}

    updateStats() {
        if (!DOM.totalItems || !DOM.completedItems || !DOM.inProgressItems || !DOM.notCompletedItems) {
            return;
        }
        
        if (!AppState.currentData.length) {
            DOM.totalItems.textContent = '0';
            DOM.completedItems.textContent = '0';
            DOM.inProgressItems.textContent = '0';
            DOM.notCompletedItems.textContent = '0';
            return;
        }
        
        const total = AppState.currentData.length;
        const completed = AppState.currentData.filter(row => row[5] === '已完成').length;
        const inProgress = AppState.currentData.filter(row => row[5] === '进行中').length;
        const notCompleted = AppState.currentData.filter(row => row[5] === '未完成').length;
        
        DOM.totalItems.textContent = total;
        DOM.completedItems.textContent = completed;
        DOM.inProgressItems.textContent = inProgress;
        DOM.notCompletedItems.textContent = notCompleted;
    }

    async loadFileList() {
    try {
        Utils.showNotification('正在加载文件列表...', 'info');
        const response = await fetch('/file_list');
        
        if (!response.ok) {
            throw new Error(`获取文件列表失败: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        this.renderFileList(data.files || []);
        Utils.showNotification('文件列表加载成功', 'success');
    } catch (error) {
        console.error('加载文件列表失败:', error);
        Utils.showNotification(`❌ 加载文件列表失败: ${error.message}`, 'error');
    }
}

    validateFile(file) {
    const errors = [];
    
    // 检查文件类型
    const allowedExtensions = ['.csv', '.sti'];
    const fileExtension = file.name.toLowerCase().slice(-4);
    if (!allowedExtensions.includes(fileExtension)) {
        errors.push('只支持 CSV 和 STI 格式的文件');
    }
    
    // 检查文件大小 (10MB)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
        errors.push('文件大小不能超过 10MB');
    }
    
    // 检查文件名
    if (file.name.length > 255) {
        errors.push('文件名过长');
    }
    
    // 检查特殊字符
    const invalidChars = /[<>:"/\\|?*]/;
    if (invalidChars.test(file.name)) {
        errors.push('文件名包含非法字符');
    }
    
    return errors;
}


    async loadAllFiles() {
        try {
            const response = await fetch('/all_files');
            const data = await response.json();
            
            if (data.error) {
                Utils.showNotification(`❌ ${data.error}`, 'error');
                return;
            }
            
            this.renderFileList(data.files, true);
        } catch (error) {
            console.error('加载所有文件失败:', error);
            Utils.showNotification('❌ 加载文件列表时出错', 'error');
        }
    }

    renderFileList(files, showAll = false) {
    if (!DOM.fileList) return;
    
    if (!files || files.length === 0) {
        DOM.fileList.innerHTML = `
            <div class="empty-state">
                <div class="icon">📁</div>
                <div>暂无文件</div>
            </div>
        `;
        return;
    }
    
    DOM.fileList.innerHTML = files.map(file => `
        <div class="file-card" data-filename="${file.filename}">
            <div class="file-name">${file.filename}</div>
            <div class="file-meta">
                <span>${Utils.formatFileSize(file.size)}</span>
                <span>${Utils.formatDate(file.created_at)}</span>
            </div>
            ${file.description ? `<div style="margin-top: 8px; color: #64748b; font-size: 13px;">${file.description}</div>` : ''}
            ${showAll ? `<div style="margin-top: 8px; color: #94a3b8; font-size: 12px;">所有者: ${file.owner}</div>` : ''}
            <div class="file-actions">
                <button class="btn-outline" style="padding: 6px 12px; font-size: 12px;" onclick="app.openExistingFile('${file.filename}')">
                    打开
                </button>
                ${!showAll ? `
                <button class="btn-danger" style="padding: 6px 12px; font-size: 12px;" onclick="app.deleteFile('${file.filename}')">
                    删除
                </button>
                ` : ''}
            </div>
        </div>
    `).join('');
}

    async openExistingFile(filename) {
    try {
        console.log(`尝试打开文件: ${filename}`);
        Utils.showNotification('正在打开文件...', 'info');
        
        const response = await fetch(`/open_file/${encodeURIComponent(filename)}`);
        
        if (!response.ok) {
            if (response.status === 404) {
                throw new Error(`文件不存在: ${filename}`);
            } else {
                throw new Error(`服务器错误: ${response.status}`);
            }
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // 成功打开文件
        AppState.currentFilename = filename;
        AppState.currentData = data.data || [];
        this.renderTable();
        this.updateStats();
        
        // 显示统计栏
        if (DOM.statsBar) {
            DOM.statsBar.style.display = 'grid';
        }
        
        Utils.showNotification(`成功打开文件: ${filename}`, 'success');
        
        // 保存最近打开的文件
        localStorage.setItem('lastOpenedFile', filename);
        
        // 加入文件编辑
        this.joinFileEditing(filename);
        
    } catch (error) {
        console.error('打开文件错误:', error);
        Utils.showNotification(`❌ 打开文件失败: ${error.message}`, 'error');
        
        // 如果文件不存在，清除本地存储的记录
        if (error.message.includes('不存在')) {
            localStorage.removeItem('lastOpenedFile');
        }
    }
}

    async deleteFile(filename) {
        if (!confirm(`确定要删除文件 "${filename}" 吗？此操作不可撤销。`)) {
            return;
        }
        
        try {
            const response = await fetch(`/delete_file/${encodeURIComponent(filename)}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.error) {
                Utils.showNotification(`❌ ${data.error}`, 'error');
                return;
            }
            
            Utils.showNotification(`✅ ${data.message}`, 'success');
            
            // 如果删除的是当前打开的文件，清空当前数据
            if (AppState.currentFilename === filename) {
                AppState.currentData = [];
                AppState.currentFilename = '';
                this.renderTable();
                this.updateStats();
                if (DOM.statsBar) DOM.statsBar.style.display = 'none';
            }
            
            this.loadFileList();
        } catch (error) {
            console.error('删除文件失败:', error);
            Utils.showNotification('❌ 删除文件时出错', 'error');
        }
    }

    async saveFile() {
        if (!AppState.currentData.length) {
            Utils.showNotification('❌ 没有数据可保存', 'warning');
            return;
        }
        
        const filename = prompt('请输入文件名:', AppState.currentFilename || 'materials') || 'materials';
        const description = prompt('请输入文件描述（可选）:') || '';
        
        try {
            const response = await fetch('/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filename: filename,
                    data: AppState.currentData,
                    description: description
                })
            });
            
            const data = await response.json();
            
            if (data.error) {
                Utils.showNotification(`❌ ${data.error}`, 'error');
                return;
            }
            
            AppState.currentFilename = data.file_info.filename;
            Utils.showNotification(`✅ ${data.message}`, 'success');
            this.loadFileList();
        } catch (error) {
            console.error('保存文件失败:', error);
            Utils.showNotification('❌ 保存文件时出错', 'error');
        }
    }

    initializeSocket() {
    try {
        // 确保只初始化一次
        if (AppState.socket && AppState.socket.connected) {
            AppState.socket.disconnect();
        }

        // 使用更稳定的配置
        AppState.socket = io({
            reconnection: true,
            reconnectionAttempts: 10,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            timeout: 20000,
            transports: ['websocket', 'polling']
        });
        
        AppState.socket.on('connect', () => {
            console.log('✅ WebSocket 连接已建立，连接ID:', AppState.socket.id);
            if (DOM.connectionDot) DOM.connectionDot.classList.add('connected');
            if (DOM.connectionStatus) DOM.connectionStatus.textContent = '已连接';
            Utils.showNotification('✅ WebSocket连接已建立', 'success');
            
            // 重新加入当前文件（如果有）
            if (AppState.currentFilename && AppState.currentUser) {
                this.joinFileEditing(AppState.currentFilename);
            }
        });
        
        AppState.socket.on('disconnect', (reason) => {
            console.log('❌ WebSocket 连接断开:', reason);
            if (DOM.connectionDot) DOM.connectionDot.classList.remove('connected');
            if (DOM.connectionStatus) DOM.connectionStatus.textContent = '连接断开';
            
            if (reason === 'io server disconnect') {
                // 服务器主动断开，需要手动重连
                AppState.socket.connect();
            }
        });
        
        AppState.socket.on('reconnect', (attemptNumber) => {
            console.log(`✅ WebSocket 重新连接成功，尝试次数: ${attemptNumber}`);
            if (DOM.connectionDot) DOM.connectionDot.classList.add('connected');
            if (DOM.connectionStatus) DOM.connectionStatus.textContent = '已连接';
            Utils.showNotification('✅ WebSocket连接已恢复', 'success');
            
            // 重新加入当前文件
            if (AppState.currentFilename && AppState.currentUser) {
                this.joinFileEditing(AppState.currentFilename);
            }
        });
        
        AppState.socket.on('reconnect_error', (error) => {
            console.log('❌ WebSocket 重新连接失败:', error);
        });
        
        AppState.socket.on('reconnect_failed', () => {
            console.log('❌ WebSocket 重新连接彻底失败');
            Utils.showNotification('❌ WebSocket连接失败，请刷新页面', 'error');
        });
        
        // 处理项目更新事件 - 修复重复更新问题
        AppState.socket.on('item_updated', (data) => {
            console.log('收到项目更新:', data);
            if (data.filename === AppState.currentFilename) {
                // 确保行索引有效
                if (data.rowIndex >= 0 && data.rowIndex < AppState.currentData.length) {
                    // 只有状态不同时才更新，避免循环更新
                    if (AppState.currentData[data.rowIndex][5] !== data.status) {
                        AppState.currentData[data.rowIndex][5] = data.status;
                        this.renderTable();
                        this.updateStats();
                        
                        // 显示通知，但不显示自己的操作
                        if (data.username !== AppState.currentUser) {
                            Utils.showNotification(`🔄 ${data.username} 更新了项目状态`, 'info');
                        }
                    }
                }
            }
        });
        
        // 处理文件数据更新事件
        AppState.socket.on('file_data_updated', (data) => {
            console.log('收到文件数据更新:', data);
            if (data.filename === AppState.currentFilename) {
                AppState.currentData = data.data || [];
                this.renderTable();
                this.updateStats();
                Utils.showNotification(`🔄 文件数据已同步更新`, 'info');
            }
        });
        
        AppState.socket.on('user_joined', (data) => {
            if (data.username !== AppState.currentUser) {
                Utils.showNotification(`👥 ${data.username} 加入了文件编辑`, 'info');
            }
        });
        
        AppState.socket.on('user_left', (data) => {
            Utils.showNotification(`👋 ${data.username} 离开了文件编辑`, 'info');
        });
        
        AppState.socket.on('file_data', (data) => {
            console.log('收到初始文件数据:', data);
            if (data.filename === AppState.currentFilename) {
                AppState.currentData = data.data || [];
                this.renderTable();
                this.updateStats();
            }
        });
        
    } catch (error) {
        console.error('Socket.IO 初始化失败:', error);
        if (DOM.connectionStatus) {
            DOM.connectionStatus.textContent = 'Socket.IO 连接失败';
        }
    }
}

// 加入文件编辑功能
joinFileEditing(filename) {
    if (AppState.socket && AppState.socket.connected && AppState.currentUser) {
        console.log(`加入文件编辑: ${filename}, 用户: ${AppState.currentUser}`);
        AppState.socket.emit('join_file', {
            filename: filename,
            username: AppState.currentUser
        });
        
        // 发送文件数据到服务器进行同步
        if (AppState.currentData.length > 0) {
            setTimeout(() => {
                AppState.socket.emit('file_loaded', {
                    filename: filename,
                    data: AppState.currentData
                });
                
                // 同时发送同步请求
                AppState.socket.emit('sync_file_data', {
                    filename: filename,
                    data: AppState.currentData
                });
            }, 500);
        }
    } else {
        console.warn('无法加入文件编辑: Socket 未连接或用户未登录');
    }
}

    joinFileEditing(filename) {
    if (AppState.socket && AppState.socket.connected && AppState.currentUser) {
        console.log(`加入文件编辑: ${filename}, 用户: ${AppState.currentUser}`);
        AppState.socket.emit('join_file', {
            filename: filename,
            username: AppState.currentUser
        });
        
        // 发送文件数据到服务器
        if (AppState.currentData.length > 0) {
            setTimeout(() => {
                AppState.socket.emit('file_loaded', {
                    filename: filename,
                    data: AppState.currentData
                });
            }, 1000);
        }
    } else {
        console.warn('无法加入文件编辑: Socket 未连接或用户未登录');
    }
}

    setupAutoSave() {
        AppState.autoSaveInterval = setInterval(() => {
            if (AppState.currentData.length > 0 && AppState.currentFilename) {
                this.autoSave();
            }
        }, CONFIG.AUTO_SAVE_INTERVAL);
    }

    async autoSave() {
        if (!AppState.currentData.length || !AppState.currentFilename) return;
        
        const currentDataStr = JSON.stringify(AppState.currentData);
        if (currentDataStr === AppState.lastSavedData) return;

        try {
            const response = await fetch('/auto_save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filename: AppState.currentFilename,
                    data: AppState.currentData
                })
            });
            
            const data = await response.json();
            if (data.success) {
                AppState.lastSavedData = currentDataStr;
                console.log('✅ 自动保存成功');
            }
        } catch (error) {
            console.error('自动保存失败:', error);
        }
    }

    setupMobileFeatures() {
        if (AppState.isMobile) {
            document.body.classList.add('mobile-device');
            this.setupMobileEventListeners();
        }
    }

    setupMobileEventListeners() {
        // 移动端状态按钮
        if (DOM.mobileInProgressBtn) {
            DOM.mobileInProgressBtn.addEventListener('click', () => {
                this.changeStatus(AppState.mobileSelectedRow, 'in-progress');
            });
        }
        
        if (DOM.mobileCompletedBtn) {
            DOM.mobileCompletedBtn.addEventListener('click', () => {
                this.changeStatus(AppState.mobileSelectedRow, 'completed');
            });
        }
        
        if (DOM.mobileNotCompletedBtn) {
            DOM.mobileNotCompletedBtn.addEventListener('click', () => {
                this.changeStatus(AppState.mobileSelectedRow, 'not-completed');
            });
        }
        
        if (DOM.mobileCancelBtn) {
            DOM.mobileCancelBtn.addEventListener('click', () => {
                if (DOM.mobileToolbar) DOM.mobileToolbar.style.display = 'none';
                AppState.mobileSelectedRow = null;
            });
        }
    }

}

// 创建全局app实例
const app = new MaterialsApp();

// 页面加载完成后初始化
console.log('🧱 原理图材料列表查看器已加载');
