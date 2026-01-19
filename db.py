import sqlite3
import os

# 数据库文件路径
DB_FILE = os.path.join(os.path.dirname(__file__), 'repos.db')

def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 创建仓库信息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS repositories (
            name TEXT PRIMARY KEY,
            description TEXT,
            language TEXT,
            is_private INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_repo_info(repo_name):
    """获取仓库信息"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM repositories WHERE name = ?', (repo_name,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'name': result[0],
            'description': result[1],
            'language': result[2],
            'is_private': result[3],
            'created_at': result[4],
            'updated_at': result[5]
        }
    return None

def update_repo_info(repo_name, description='', language='', is_private=0):
    """更新仓库信息"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO repositories (name, description, language, is_private, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (repo_name, description, language, is_private))
    
    conn.commit()
    conn.close()

def get_all_repo_info():
    """获取所有仓库信息"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT name, description, language FROM repositories')
    results = cursor.fetchall()
    conn.close()
    
    return {row[0]: {'description': row[1], 'language': row[2]} for row in results}
