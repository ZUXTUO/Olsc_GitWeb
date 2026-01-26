import sqlite3
import os

# 数据库文件路径
DB_FILE = os.path.join(os.path.dirname(__file__), 'repos.db')

def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 创建仓库信息表
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS repositories (
            name TEXT PRIMARY KEY,
            description TEXT,
            language TEXT,
            is_private INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS releases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_name TEXT,
            tag_name TEXT,
            target_commitish TEXT,
            name TEXT,
            body TEXT,
            is_draft INTEGER DEFAULT 0,
            is_prerelease INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            published_at TIMESTAMP,
            FOREIGN KEY (repo_name) REFERENCES repositories(name)
        );

        CREATE TABLE IF NOT EXISTS release_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            release_id INTEGER,
            name TEXT,
            content_type TEXT,
            size INTEGER,
            path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (release_id) REFERENCES releases(id)
        );
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

def create_release(repo_name, tag_name, target_commitish, name, body, is_draft=0, is_prerelease=0):
    """创建新发行版"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO releases (repo_name, tag_name, target_commitish, name, body, is_draft, is_prerelease, published_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (repo_name, tag_name, target_commitish, name, body, is_draft, is_prerelease))
    release_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return release_id

def add_release_asset(release_id, name, content_type, size, path):
    """添加发行版资产"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO release_assets (release_id, name, content_type, size, path)
        VALUES (?, ?, ?, ?, ?)
    ''', (release_id, name, content_type, size, path))
    asset_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return asset_id

def get_repo_releases(repo_name):
    """获取仓库的所有发行版"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, tag_name, name, body, created_at, published_at, target_commitish, is_prerelease 
        FROM releases 
        WHERE repo_name = ? 
        ORDER BY created_at DESC
    ''', (repo_name,))
    releases = []
    for row in cursor.fetchall():
        release_id = row[0]
        # 获取资产
        asset_cursor = conn.cursor()
        asset_cursor.execute('SELECT id, name, size, created_at FROM release_assets WHERE release_id = ?', (release_id,))
        assets = [{'id': r[0], 'name': r[1], 'size': r[2], 'created_at': r[3]} for r in asset_cursor.fetchall()]
        
        releases.append({
            'id': release_id,
            'tag_name': row[1],
            'name': row[2],
            'body': row[3],
            'created_at': row[4],
            'published_at': row[5],
            'target_commitish': row[6],
            'is_prerelease': row[7],
            'assets': assets
        })
    conn.close()
    return releases

def get_release(release_id):
    """获取单个发行版"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM releases WHERE id = ?', (release_id,))
    row = cursor.fetchone()
    
    if row:
        asset_cursor = conn.cursor()
        asset_cursor.execute('SELECT id, name, size, created_at FROM release_assets WHERE release_id = ?', (release_id,))
        assets = [{'id': r[0], 'name': r[1], 'size': r[2], 'created_at': r[3]} for r in asset_cursor.fetchall()]
        
        release = {
            'id': row[0],
            'repo_name': row[1],
            'tag_name': row[2],
            'target_commitish': row[3],
            'name': row[4],
            'body': row[5],
            'is_draft': row[6],
            'is_prerelease': row[7],
            'created_at': row[8],
            'published_at': row[9],
            'assets': assets
        }
        conn.close()
        return release
    conn.close()
    return None

def get_asset(asset_id):
    """获取资产信息"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM release_assets WHERE id = ?', (asset_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            'id': row[0],
            'release_id': row[1],
            'name': row[2],
            'content_type': row[3],
            'size': row[4],
            'path': row[5],
            'created_at': row[6]
        }
    return None

def delete_release(release_id):
    """删除发行版"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # 获取所有资产路径以便删除文件
    cursor.execute('SELECT path FROM release_assets WHERE release_id = ?', (release_id,))
    paths = [row[0] for row in cursor.fetchall()]
    
    cursor.execute('DELETE FROM release_assets WHERE release_id = ?', (release_id,))
    cursor.execute('DELETE FROM releases WHERE id = ?', (release_id,))
    conn.commit()
    conn.close()
    return paths
