import os
import stat
import subprocess
import json
import shutil
import mimetypes
import hashlib
from flask import Flask, request, jsonify, render_template, redirect, url_for, abort, send_file, flash, get_flashed_messages, Response, session
from functools import wraps
from werkzeug.utils import secure_filename
import datetime


try:
    import markdown
except ImportError:
    markdown = None


import db

app = Flask(__name__)
app.secret_key = 'git-manager-secret-key-very-secure-random-string-2026'


app.config['MAX_CONTENT_LENGTH'] = None




BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
KEY_FILE = os.path.join(BASE_DIR, 'key.txt')
PORT = 8080


if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


db.init_db()

def get_password_hash():
    """从 key.txt 读取密码哈希"""
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:

                if len(content) != 64:
                    return hashlib.sha256(content.encode('utf-8')).hexdigest()
                return content
    return None

def require_auth(f):
    """装饰器：要求认证"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        password_hash = get_password_hash()

        if password_hash and not session.get('authenticated'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_repo_path(repo_name):
    """安全地解析仓库路径，防止目录遍历。"""

    
    if not repo_name or '..' in repo_name or '/' in repo_name or '\\' in repo_name:
        return None
    

    real_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name

    
    path = os.path.join(DATA_DIR, real_name)

    
    if os.path.exists(path) and os.path.isdir(path):
        return path
    return None

def run_git_command(repo_path, command_args):
    """在指定的仓库中运行 git 命令。"""
    try:

        env = os.environ.copy()
        env['GIT_TERMINAL_PROMPT'] = '0'
        
        result = subprocess.run(
            ['git', '-c', 'core.quotepath=false'] + command_args,
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False
        )
        

        stdout = result.stdout.decode('utf-8', errors='replace')
        stderr = result.stderr.decode('utf-8', errors='replace')
        
        return {
            'success': result.returncode == 0,
            'stdout': stdout,
            'stderr': stderr
        }
    except Exception as e:
        return { 'success': False, 'error': str(e) }

def git_http_backend(repo_path, service):
    """直接使用 Git 命令实现 Smart HTTP 协议，避免 git http-backend 的路径问题。"""

    
    if not repo_path:
        return Response("未找到仓库", status=404)
    

    git_dir = os.path.join(repo_path, '.git')
    if not os.path.exists(git_dir):
        git_dir = repo_path
    

    

    if service == '/info/refs':
        service_name = request.args.get('service', '')

        
        if service_name == 'git-upload-pack':

            try:
                result = subprocess.run(
                    ['git', 'upload-pack', '--stateless-rpc', '--advertise-refs', git_dir],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )
                
                if result.returncode != 0:

                    return Response(result.stderr, status=500, mimetype='text/plain')
                

                response_data = f'001e# service=git-upload-pack\n0000'.encode() + result.stdout
                return Response(
                    response_data,
                    status=200,
                    mimetype='application/x-git-upload-pack-advertisement'
                )
            except Exception as e:

                return Response(str(e), status=500, mimetype='text/plain')
                
        elif service_name == 'git-receive-pack':

            try:
                result = subprocess.run(
                    ['git', 'receive-pack', '--stateless-rpc', '--advertise-refs', git_dir],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )
                
                if result.returncode != 0:

                    return Response(result.stderr, status=500, mimetype='text/plain')
                

                response_data = f'001f# service=git-receive-pack\n0000'.encode() + result.stdout
                return Response(
                    response_data,
                    status=200,
                    mimetype='application/x-git-receive-pack-advertisement'
                )
            except Exception as e:

                return Response(str(e), status=500, mimetype='text/plain')
    
    elif service == '/git-upload-pack':

        try:
            result = subprocess.run(
                ['git', 'upload-pack', '--stateless-rpc', git_dir],
                input=request.data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            
            if result.returncode != 0:

                return Response(result.stderr, status=500, mimetype='text/plain')
            
            return Response(
                result.stdout,
                status=200,
                mimetype='application/x-git-upload-pack-result'
            )
        except Exception as e:

            return Response(str(e), status=500, mimetype='text/plain')
    
    elif service == '/git-receive-pack':

        try:
            result = subprocess.run(
                ['git', 'receive-pack', '--stateless-rpc', git_dir],
                input=request.data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            
            if result.returncode != 0:

                return Response(result.stderr, status=500, mimetype='text/plain')
            
            return Response(
                result.stdout,
                status=200,
                mimetype='application/x-git-receive-pack-result'
            )
        except Exception as e:

            return Response(str(e), status=500, mimetype='text/plain')
    

    return Response("Unknown service", status=404)

@app.template_filter('basename')
def basename_filter(s):
    return os.path.basename(s)

@app.template_filter('dirname')
def dirname_filter(s):
    return os.path.dirname(s)

@app.template_filter('markdown')
def markdown_filter(s):
    if not s: return ""
    if markdown:
        return markdown.markdown(s, extensions=['fenced_code', 'tables', 'nl2br'])
    return s

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    password_hash = get_password_hash()

    if not password_hash:
        session['authenticated'] = True
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        input_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        if input_hash == password_hash:
            session['authenticated'] = True
            return redirect(url_for('index'))
        else:
            flash('密码错误', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """登出"""
    session.pop('authenticated', None)
    return redirect(url_for('login'))

@app.route('/')
@require_auth
def index():
    """列出所有仓库。"""
    repos = []
    repo_info_map = db.get_all_repo_info()
    
    if os.path.exists(DATA_DIR):
        for d in os.listdir(DATA_DIR):
            if d.startswith('.') or d.endswith('_temp_init'): continue
            path = os.path.join(DATA_DIR, d)
            if os.path.isdir(path):

                is_git = os.path.exists(os.path.join(path, '.git')) or \
                         (os.path.exists(os.path.join(path, 'HEAD')) and os.path.exists(os.path.join(path, 'config')))
                info = repo_info_map.get(d, {})
                repos.append({ 
                    'name': d, 
                    'is_git': is_git,
                    'description': info.get('description', ''),
                    'language': info.get('language', '混合语言')
                })
    return render_template('index.html', repos=repos)

@app.route('/search')
@require_auth
def search():
    """搜索项目、代码和提交"""
    query = request.args.get('q', '').strip()
    filter_type = request.args.get('type', '')
    
    if not query:
        return redirect(url_for('index'))
    
    query_lower = query.lower()
    

    repositories = []
    repo_info_map = db.get_all_repo_info()
    
    if os.path.exists(DATA_DIR):
        for d in os.listdir(DATA_DIR):
            if d.startswith('.') or d.endswith('_temp_init'): continue
            path = os.path.join(DATA_DIR, d)
            if os.path.isdir(path):
                info = repo_info_map.get(d, {})
                description = info.get('description', '')
                language = info.get('language', '')
                

                if (query_lower in d.lower() or 
                    query_lower in description.lower() or 
                    query_lower in language.lower()):
                    repositories.append({
                        'name': d,
                        'description': description,
                        'language': language
                    })
    

    code_results = []
    if os.path.exists(DATA_DIR):
        for repo_name in os.listdir(DATA_DIR):
            if repo_name.startswith('.') or repo_name.endswith('_temp_init'): continue
            repo_path = os.path.join(DATA_DIR, repo_name)
            if not os.path.isdir(repo_path): continue
            

            result = run_git_command(repo_path, ['grep', '-n', '-i', '--', query])
            if result['success'] and result['stdout']:
                for line in result['stdout'].splitlines()[:10]:

                    parts = line.split(':', 2)
                    if len(parts) >= 3:
                        filename, line_num, content = parts
                        code_results.append({
                            'repo': repo_name,
                            'file': filename,
                            'line_number': line_num,
                            'snippet': content.strip(),
                            'ref': 'HEAD'
                        })
    

    commits = []
    if os.path.exists(DATA_DIR):
        for repo_name in os.listdir(DATA_DIR):
            if repo_name.startswith('.') or repo_name.endswith('_temp_init'): continue
            repo_path = os.path.join(DATA_DIR, repo_name)
            if not os.path.isdir(repo_path): continue
            

            result = run_git_command(repo_path, [
                'log', 
                '--all',
                '--grep=' + query, 
                '--author=' + query,
                '--pretty=format:%H|%an|%ar|%s',
                '-n', '10'
            ])
            
            if result['success'] and result['stdout']:
                for line in result['stdout'].splitlines():
                    parts = line.split('|', 3)
                    if len(parts) >= 4:
                        commits.append({
                            'repo': repo_name,
                            'hash': parts[0],
                            'author': parts[1],
                            'date': parts[2],
                            'message': parts[3]
                        })
    

    total_results = len(repositories) + len(code_results) + len(commits)
    
    return render_template('search.html',
                          query=query,
                          filter_type=filter_type,
                          repositories=repositories if not filter_type or filter_type == 'repositories' else [],
                          code_results=code_results if not filter_type or filter_type == 'code' else [],
                          commits=commits if not filter_type or filter_type == 'commits' else [],
                          total_results=total_results,
                          repo_count=len(repositories),
                          code_count=len(code_results),
                          commit_count=len(commits))

@app.route('/repo/<repo_name>/edit', methods=['GET', 'POST'])
@require_auth
def edit_repo_info(repo_name):
    """编辑仓库信息"""
    clean_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name
    repo_path = get_repo_path(clean_name)
    if not repo_path:
        abort(404)
    
    if request.method == 'POST':
        description = request.form.get('description', '')
        language = request.form.get('language', '')
        db.update_repo_info(clean_name, description, language)
        flash('仓库信息已更新', 'success')
        return redirect(url_for('index'))
    
    info = db.get_repo_info(clean_name) or {}
    return render_template('edit_repo.html', 
                          repo_name=clean_name, 
                          description=info.get('description', ''),
                          language=info.get('language', ''))

@app.route('/create', methods=['POST'])
@require_auth
def create_repo():
    """创建一个新的 git 仓库。"""
    name = request.form.get('name')
    if not name or '..' in name or '/' in name:
        return jsonify({ 'error': '无效的名称' }), 400
    

    if name.endswith('.git'): name = name[:-4]
    
    repo_path = os.path.join(DATA_DIR, name)


    temp_path = os.path.join(DATA_DIR, f"{name}_temp_init")
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)
    os.makedirs(temp_path)
    
    try:

        run_git_command(temp_path, ['init'])
        

        readme_path = os.path.join(temp_path, 'README.md')
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(f'# {name}\n\n这是一个新创建的 Git 仓库。\n')
        
        run_git_command(temp_path, ['add', 'README.md'])
        run_git_command(temp_path, ['commit', '-m', 'Initial commit'])
        


        if os.path.exists(repo_path):
             shutil.rmtree(repo_path)
             
        run_git_command(temp_path, ['clone', '--bare', '.', repo_path])
        


        run_git_command(repo_path, ['config', 'http.receivepack', 'true'])

        run_git_command(repo_path, ['config', 'receive.denyNonFastForwards', 'false'])

        
    except Exception as e:
        print(f"创建仓库失败: {e}")
        return jsonify({ 'error': f'创建失败: {str(e)}' }), 500
    finally:

        if os.path.exists(temp_path):

            def remove_readonly(func, path, excinfo):
                os.chmod(path, stat.S_IWRITE)
                func(path)
                
            try:
                shutil.rmtree(temp_path, onerror=remove_readonly)
            except Exception as e:
                print(f"清理临时目录失败: {e}")
    
    return redirect(url_for('view_repo', repo_name=name))


@app.route('/<repo_name>.git/info/refs')
def git_info_refs(repo_name):

    repo_path = get_repo_path(repo_name)

    if not repo_path:
        abort(404)

    return git_http_backend(repo_path, '/info/refs')

@app.route('/<repo_name>.git/git-upload-pack', methods=['POST'])
def git_upload_pack(repo_name):
    repo_path = get_repo_path(repo_name)
    if not repo_path:
        abort(404)
    return git_http_backend(repo_path, '/git-upload-pack')

@app.route('/<repo_name>.git/git-receive-pack', methods=['POST'])
def git_receive_pack(repo_name):
    repo_path = get_repo_path(repo_name)
    if not repo_path:
        abort(404)
    return git_http_backend(repo_path, '/git-receive-pack')


@app.route('/<repo_name>.git/HEAD')
def git_head(repo_name):
    """提供 HEAD 文件。"""
    repo_path = get_repo_path(repo_name)
    if not repo_path:
        abort(404)
    head_file = os.path.join(repo_path, '.git', 'HEAD')
    if os.path.exists(head_file):
        return send_file(head_file, mimetype='text/plain')
    abort(404)

@app.route('/<repo_name>.git/objects/<path:objpath>')
def git_objects(repo_name, objpath):
    """提供对象文件。"""
    repo_path = get_repo_path(repo_name)
    if not repo_path:
        abort(404)
    obj_file = os.path.join(repo_path, '.git', 'objects', objpath)
    if os.path.exists(obj_file) and os.path.isfile(obj_file):

        if objpath.endswith('/pack'):
            mimetype = 'application/x-git-packed-objects'
        elif objpath.endswith('.pack'):
            mimetype = 'application/x-git-packed-objects'
        elif objpath.endswith('.idx'):
            mimetype = 'application/x-git-packed-objects-toc'
        else:
            mimetype = 'application/x-git-loose-object'
        return send_file(obj_file, mimetype=mimetype)
    abort(404)

@app.route('/<repo_name>.git/refs/<path:refpath>')
def git_refs(repo_name, refpath):
    """提供引用文件。"""
    repo_path = get_repo_path(repo_name)
    if not repo_path:
        abort(404)
    ref_file = os.path.join(repo_path, '.git', 'refs', refpath)
    if os.path.exists(ref_file) and os.path.isfile(ref_file):
        return send_file(ref_file, mimetype='text/plain')
    abort(404)


def get_repo_refs(repo_path):
    """获取所有分支和标签。"""
    branches = []
    tags = []
    

    res_b = run_git_command(repo_path, ['branch', '--format=%(refname:short)'])
    if res_b['success']:
        branches = [b.strip() for b in res_b['stdout'].splitlines() if b.strip()]
    

    res_t = run_git_command(repo_path, ['tag'])
    if res_t['success']:
        tags = [t.strip() for t in res_t['stdout'].splitlines() if t.strip()]
        
    return { 'branches': branches, 'tags': tags }

@app.route('/<repo_name>/')
def view_repo(repo_name):
    """重定向到默认分支。"""
    clean_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name
    repo_path = get_repo_path(clean_name)
    if not repo_path: abort(404)
    
    res = run_git_command(repo_path, ['rev-parse', '--abbrev-ref', 'HEAD'])
    ref = res['stdout'].strip() if res['success'] and res['stdout'].strip() != 'HEAD' else 'master'
    

    res_log = run_git_command(repo_path, ['log', '-n', '1'])
    if not res_log['success']:

        return redirect(url_for('view_tree', repo_name=clean_name, ref='HEAD'))

    return redirect(url_for('view_tree', repo_name=clean_name, ref=ref))

@app.route('/<repo_name>/tree/<ref>/', defaults={ 'subpath': '' })
@app.route('/<repo_name>/tree/<ref>/<path:subpath>')
def view_tree(repo_name, ref, subpath=''):
    """查看仓库特定引用和路径的文件树。"""
    clean_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name
    repo_path = get_repo_path(clean_name)
    if not repo_path: abort(404)


    if ref == 'HEAD':
        res = run_git_command(repo_path, ['rev-parse', '--abbrev-ref', 'HEAD'])
        display_ref = res['stdout'].strip() if res['success'] and res['stdout'].strip() != 'HEAD' else 'HEAD'
    else:
        display_ref = ref


    refs = get_repo_refs(repo_path)
    


    target = f"{ref}:{subpath.strip('/')}" if subpath.strip('/') else ref
    
    res = run_git_command(repo_path, ['ls-tree', '-l', target])
    
    items = []
    if res['success']:
        for line in res['stdout'].splitlines():

            parts = line.split(None, 4)
            if len(parts) < 5: continue
            
            mode, obj_type, sha, size, name = parts
            is_dir = obj_type == 'tree'
            

            file_path = os.path.join(subpath, name).replace('\\', '/') if subpath else name
            commit_res = run_git_command(repo_path, ['log', '-1', '--format=%H|%s|%ar', ref, '--', file_path])
            commit_msg = ''
            commit_time = ''
            if commit_res['success'] and commit_res['stdout'].strip():
                commit_parts = commit_res['stdout'].strip().split('|', 2)
                if len(commit_parts) >= 2:
                    commit_msg = commit_parts[1]
                    commit_time = commit_parts[2] if len(commit_parts) >= 3 else ''
            
            items.append({
                'name': name,
                'path': os.path.join(subpath, name).replace('\\', '/'),
                'is_dir': is_dir,
                'size': size if size != '-' else 0,
                'sha': sha,
                'commit_message': commit_msg,
                'commit_time': commit_time
            })
    elif not subpath:


        pass


    items.sort(key=lambda x: (not x['is_dir'], x['name']))
    

    path_for_log = subpath if subpath else '.'
    latest_commit_res = run_git_command(repo_path, ['log', '-1', '--format=%H|%an|%ar|%s', ref, '--', path_for_log])
    latest_commit = None
    if latest_commit_res['success'] and latest_commit_res['stdout'].strip():
        commit_parts = latest_commit_res['stdout'].strip().split('|', 3)
        if len(commit_parts) >= 4:
            latest_commit = {
                'hash': commit_parts[0],
                'author': commit_parts[1],
                'time': commit_parts[2],
                'message': commit_parts[3]
            }
    

    git_status = run_git_command(repo_path, ['status', '-s'])
    
    readme_content = None
    readme_is_markdown = False
    

    for readme in ['README.md', 'README.txt', 'readme.md']:
        readme_path = os.path.join(subpath, readme).replace('\\', '/')
        r_target = f"{ref}:{readme_path}"
        res_r = run_git_command(repo_path, ['show', r_target])
        if res_r['success']:
            content = res_r['stdout']
            if readme.lower().endswith('.md'):
                readme_content = content
                readme_is_markdown = True
            else:
                readme_content = f"<pre>{content}</pre>"
            break

    return render_template('repo.html', 
                           repo_name=clean_name, 
                           ref=ref,
                           display_ref=display_ref,
                           refs=refs,
                           current_path=subpath, 
                           items=items,
                           latest_commit=latest_commit, 
                           readme=readme_content,
                           readme_is_markdown=readme_is_markdown,
                           status=git_status['stdout'] if ref == 'HEAD' or ref == display_ref else None)

@app.route('/<repo_name>/blob/<ref>/<path:filepath>')
def view_file(repo_name, ref, filepath):
    """查看特定文件在特定引用的内容。"""
    clean_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name
    repo_path = get_repo_path(clean_name)
    if not repo_path: abort(404)
    

    mime_type, _ = mimetypes.guess_type(filepath)
    ext = filepath.lower().split('.')[-1] if '.' in filepath else ''


    if ref == 'HEAD':
        res_br = run_git_command(repo_path, ['rev-parse', '--abbrev-ref', 'HEAD'])
        display_ref = res_br['stdout'].strip() if res_br['success'] and res_br['stdout'].strip() != 'HEAD' else 'HEAD'
    else:
        display_ref = ref


    if request.args.get('raw') == '1':

        try:
            target = f"{ref}:{filepath}"
            result = subprocess.run(
                ['git', 'show', target],
                cwd=repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            if result.returncode == 0:
                return Response(result.stdout, mimetype=mime_type or 'application/octet-stream')
            else:
                abort(404)
        except Exception:
            abort(500)


    target = f"{ref}:{filepath}"
    res = run_git_command(repo_path, ['show', target])
    
    if not res['success']:
        abort(404)
        


    res_info = run_git_command(repo_path, ['ls-tree', '-l', target])
    file_size_bytes = 0
    if res_info['success'] and res_info['stdout']:
        parts = res_info['stdout'].split()
        if len(parts) >= 4:
            try:
                file_size_bytes = int(parts[3])
            except ValueError:
                pass

    if file_size_bytes < 1024:
        file_size = f"{file_size_bytes} B"
    elif file_size_bytes < 1024 * 1024:
        file_size = f"{file_size_bytes / 1024:.1f} KB"
    else:
        file_size = f"{file_size_bytes / (1024 * 1024):.1f} MB"
    
    is_image = mime_type and mime_type.startswith('image/')
    is_video = mime_type and mime_type.startswith('video/')
    is_pdf = ext == 'pdf' or (mime_type and mime_type == 'application/pdf')
    is_markdown = ext in ['md', 'markdown']
    is_binary = False
    
    content = ""
    html_content = ""
    
    page = request.args.get('page', 1, type=int)
    per_page = 2000
    total_pages = 1

    try:
        if not (is_image or is_video or is_pdf):
            full_content = res['stdout']
            all_lines = full_content.splitlines(keepends=True)
            total_lines = len(all_lines)
            
            if total_lines > 0:
                total_pages = (total_lines + per_page - 1) // per_page
            else:
                total_pages = 1
            
            if page < 1: page = 1
            if page > total_pages: page = total_pages
            
            start_index = (page - 1) * per_page
            content = "".join(all_lines[start_index : start_index + per_page])
                 
            if is_markdown and markdown:
                html_content = markdown.markdown(content, extensions=['fenced_code', 'tables', 'nl2br'])
        else:
            is_binary = True
    except Exception:
        is_binary = True

    return render_template('file.html', 
                            repo_name=clean_name, 
                            ref=ref,
                            display_ref=display_ref,
                            filepath=filepath, 
                            content=content, 
                            is_markdown=is_markdown,
                            html_content=html_content,
                            is_image=is_image,
                            is_video=is_video,
                            is_pdf=is_pdf,
                            is_binary=is_binary,
                            file_size=file_size,
                            current_page=page,
                            total_pages=total_pages,
                            per_page=per_page)

@app.route('/<repo_name>/commits', defaults={'ref': 'HEAD'})
@app.route('/<repo_name>/commits/<ref>')
def view_commits(repo_name, ref):
    """查看 git 日志。"""
    clean_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name
    repo_path = get_repo_path(clean_name)
    if not repo_path: abort(404)
    
    output = run_git_command(repo_path, ['log', '--pretty=format:%H|%an|%ar|%s', '-n', '50', ref])
    commits = []
    if output['success']:
        lines = output['stdout'].splitlines()
        for line in lines:
            parts = line.split('|', 3)
            if len(parts) == 4:
                commits.append({
                    'hash': parts[0],
                    'author': parts[1],
                    'date': parts[2],
                    'message': parts[3]
                })
                
    return render_template('commits.html', repo_name=clean_name, commits=commits, ref=ref)

@app.route('/<repo_name>/commit/<commit_hash>')
def view_commit(repo_name, commit_hash):
    """查看提交差异。"""
    clean_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name
    repo_path = get_repo_path(clean_name)
    if not repo_path: abort(404)
    

    info_res = run_git_command(repo_path, ['show', '--stat', commit_hash])

    diff_res = run_git_command(repo_path, ['show', commit_hash])
    
    if not info_res['success'] or not diff_res['success']:
        flash(f"无法获取提交信息: {info_res.get('error') or diff_res.get('error') or info_res.get('stderr')}", 'error')
        return redirect(url_for('view_commits', repo_name=clean_name))

    stats = info_res.get('stdout', '')
    diff = diff_res.get('stdout', '')
    

    MAX_DIFF_SIZE = 50 * 1024
    if len(diff) > MAX_DIFF_SIZE:
        diff = diff[:MAX_DIFF_SIZE] + "\n\n... (差异过大，已自动截断以提高性能)"
    
    return render_template('diff.html', 
                           repo_name=clean_name, 
                           commit_hash=commit_hash, 
                           stats=stats, 
                           diff=diff)

@app.route('/<repo_name>/tags')
def view_tags(repo_name):
    """查看标签。"""
    clean_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name
    repo_path = get_repo_path(clean_name)
    if not repo_path: abort(404)
    
    output = run_git_command(repo_path, ['tag', '-l', '-n'])
    tags_data = []
    for line in output['stdout'].splitlines():
        if line.strip():
            parts = line.split(None, 1)
            tag_name = parts[0] if parts else line
            tag_msg = parts[1] if len(parts) > 1 else ''
            tags_data.append({ 'name': tag_name, 'message': tag_msg })
    
    return render_template('tags.html', repo_name=clean_name, tags=tags_data)

@app.route('/<repo_name>/tags/delete', methods=['POST'])
@require_auth
def delete_tag(repo_name):
    """删除标签"""
    clean_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name
    repo_path = get_repo_path(clean_name)
    if not repo_path: abort(404)
    
    tag_name = request.form.get('tag_name')
    if not tag_name:
        flash('未指定标签', 'error')
        return redirect(url_for('view_tags', repo_name=clean_name))
        
    res = run_git_command(repo_path, ['tag', '-d', tag_name])
    
    if res['success']:
        flash(f'标签 {tag_name} 已删除', 'success')
    else:
        flash(f'删除失败: {res.get("stderr", "未知错误")}', 'error')
        
    return redirect(url_for('view_tags', repo_name=clean_name))

@app.route('/<repo_name>/branches')
def view_branches(repo_name):
    """查看分支。"""
    clean_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name
    repo_path = get_repo_path(clean_name)
    if not repo_path: abort(404)
    

    output = run_git_command(repo_path, ['branch', '-v', '--format=%(refname:short)|%(committerdate:relative)|%(subject)'])
    branches_data = []
    

    current_output = run_git_command(repo_path, ['branch', '--show-current'])
    current_branch = current_output['stdout'].strip()
    
    if output['success']:
        for line in output['stdout'].splitlines():
            if line.strip():
                parts = line.split('|', 2)
                if len(parts) >= 3:
                    branch_name = parts[0].strip()

                    branches_data.append({
                        'name': branch_name,
                        'date': parts[1].strip(),
                        'message': parts[2].strip(),
                        'is_current': branch_name == current_branch
                    })
    
    return render_template('branches.html', repo_name=clean_name, branches=branches_data, current_branch=current_branch)

@app.route('/<repo_name>/branches/set', methods=['POST'])
@require_auth
def set_default_branch(repo_name):
    """设置默认分支 (HEAD)"""
    clean_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name
    repo_path = get_repo_path(clean_name)
    if not repo_path: abort(404)
    
    branch = request.form.get('branch')
    if not branch:
        flash('未指定分支', 'error')
        return redirect(url_for('view_branches', repo_name=clean_name))
    

    res = run_git_command(repo_path, ['symbolic-ref', 'HEAD', f'refs/heads/{branch}'])
    
    if res['success']:
        flash(f'默认分支已设置为 {branch}', 'success')
    else:
        flash(f'设置失败: {res.get("stderr", "未知错误")}', 'error')
        
    return redirect(url_for('view_branches', repo_name=clean_name))

@app.route('/<repo_name>/branches/create', methods=['POST'])
@require_auth
def create_branch(repo_name):
    """创建新分支"""
    clean_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name
    repo_path = get_repo_path(clean_name)
    if not repo_path: abort(404)
    
    new_branch = request.form.get('new_branch', '').strip()
    if not new_branch:
        flash('分支名称不能为空', 'error')
        return redirect(url_for('view_branches', repo_name=clean_name))
        

    if not all(c.isalnum() or c in '-_./' for c in new_branch):
         flash('分支名称包含非法字符', 'error')
         return redirect(url_for('view_branches', repo_name=clean_name))

    res = run_git_command(repo_path, ['branch', new_branch, 'HEAD'])
    
    if res['success']:
        flash(f'分支 {new_branch} 创建成功', 'success')
    else:
        flash(f'创建失败: {res.get("stderr", "未知错误")}', 'error')
        
    return redirect(url_for('view_branches', repo_name=clean_name))

@app.route('/<repo_name>/branches/delete', methods=['POST'])
@require_auth
def delete_branch(repo_name):
    """删除分支"""
    clean_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name
    repo_path = get_repo_path(clean_name)
    if not repo_path: abort(404)
    
    branch = request.form.get('branch')
    if not branch:
        flash('未指定分支', 'error')
        return redirect(url_for('view_branches', repo_name=clean_name))
    

    current = run_git_command(repo_path, ['symbolic-ref', '--short', 'HEAD'])
    if current['success'] and current['stdout'].strip() == branch:
        flash('无法删除当前默认分支，请先切换默认分支。', 'error')
        return redirect(url_for('view_branches', repo_name=clean_name))


    res = run_git_command(repo_path, ['branch', '-D', branch])
    
    if res['success']:
        flash(f'分支 {branch} 已删除', 'success')
    else:
        flash(f'删除失败: {res.get("stderr", "未知错误")}', 'error')
        
    return redirect(url_for('view_branches', repo_name=clean_name))

@app.route('/<repo_name>/compare', methods=['GET', 'POST'])
def compare_nodes(repo_name):
    """比较两个引用。"""
    clean_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name
    repo_path = get_repo_path(clean_name)
    if not repo_path: abort(404)
    
    diff_output = ""
    base = request.args.get('base', 'HEAD^')
    head = request.args.get('head', 'HEAD')
    
    if request.method == 'POST':
        base = request.form.get('base')
        head = request.form.get('head')
        return redirect(url_for('compare_nodes', repo_name=clean_name, base=base, head=head))
    
    if base and head:
        res = run_git_command(repo_path, ['diff', f'{base}...{head}'])
        diff_output = res['stdout']
        
    return render_template('compare.html', repo_name=clean_name, base=base, head=head, diff=diff_output)

@app.route('/<repo_name>/settings', methods=['GET', 'POST'])
def view_settings(repo_name):
    """仓库设置及删除。"""
    clean_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name
    repo_path = get_repo_path(clean_name)
    if not repo_path: abort(404)

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'delete_repo':
            confirm_name = request.form.get('verify_name')
            if confirm_name != clean_name:
                flash('确认名称不匹配，删除失败。', 'error')
                return redirect(url_for('view_settings', repo_name=clean_name))
            
            try:
                shutil.rmtree(repo_path)
                flash(f'仓库 {clean_name} 已成功删除。', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                flash(f'删除失败: {e}', 'error')
                return redirect(url_for('view_settings', repo_name=clean_name))

    return render_template('settings.html', repo_name=clean_name)

@app.route('/<repo_name>/action', methods=['POST'])
def git_action(repo_name):
    """处理 推送/拉取/提交 (push/pull/commit)。"""
    clean_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name
    repo_path = get_repo_path(clean_name)
    if not repo_path: return jsonify({ 'error': '未找到仓库' }), 404
    
    data = request.json
    action = data.get('action')
    
    if action == 'pull':
        res = run_git_command(repo_path, ['pull'])
    elif action == 'push':
        res = run_git_command(repo_path, ['push'])
    elif action == 'commit':
        msg = data.get('message', '通过 Web 更新')
        run_git_command(repo_path, ['add', '.'])
        res = run_git_command(repo_path, ['commit', '-m', msg])
    else:
        return jsonify({ 'error': '位置操作' }), 400
        
    return jsonify(res)

@app.route('/<repo_name>/download/<ref>')
@require_auth
def download_zip(repo_name, ref):
    """下载仓库的 ZIP 压缩包"""
    clean_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name
    repo_path = get_repo_path(clean_name)
    if not repo_path: 
        abort(404)
    
    import tempfile
    import zipfile
    from io import BytesIO
    
    try:

        result = subprocess.run(
            ['git', 'archive', '--format=zip', ref],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )
        
        if result.returncode != 0:
            flash(f'无法创建压缩包: {result.stderr.decode("utf-8", errors="replace")}', 'error')
            return redirect(url_for('view_repo', repo_name=clean_name))
        

        zip_data = BytesIO(result.stdout)
        

        filename = f"{clean_name}-{ref}.zip"
        
        return send_file(
            zip_data,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'下载失败: {str(e)}', 'error')
        return redirect(url_for('view_repo', repo_name=clean_name))

@app.route('/upload_temp_asset', methods=['POST'])
@require_auth
def upload_temp_asset():
    """上传临时文件资产 (用于带进度条的异步上传)"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file:
        filename = secure_filename(file.filename)

        timestamp = int(datetime.datetime.now().timestamp() * 1000)
        saved_filename = f"{timestamp}_{filename}"
        
        temp_dir = os.path.join(DATA_DIR, 'temp_uploads')
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        file.save(os.path.join(temp_dir, saved_filename))
        
        return jsonify({
            'success': True,
            'temp_key': saved_filename,
            'original_name': filename
        })
    return jsonify({'error': 'Unknown error'}), 500

@app.route('/<repo_name>/releases')
def view_releases(repo_name):
    """查看发布版本"""
    clean_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name
    repo_path = get_repo_path(clean_name)
    if not repo_path: abort(404)
    
    releases = db.get_repo_releases(clean_name)
    return render_template('releases.html', repo_name=clean_name, releases=releases)

@app.route('/<repo_name>/releases/new', methods=['GET', 'POST'])
@require_auth
def new_release(repo_name):
    """创建新发布版本"""
    clean_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name
    repo_path = get_repo_path(clean_name)
    if not repo_path: abort(404)
    

    tags_res = run_git_command(repo_path, ['tag', '-l'])
    tags = tags_res['stdout'].splitlines() if tags_res['success'] else []
    
    if request.method == 'POST':
        tag_name = request.form.get('tag_name')
        target_commitish = request.form.get('target_commitish', 'master')
        name = request.form.get('name')
        body = request.form.get('body')
        is_prerelease = 1 if request.form.get('is_prerelease') else 0
        
        if not tag_name:
            flash('标签名不能为空', 'error')
            return redirect(url_for('new_release', repo_name=clean_name))
            

        if tag_name not in tags:


            res = run_git_command(repo_path, ['tag', tag_name, target_commitish])
            if not res['success']:
                flash(f'创建标签失败: {res["stderr"]}', 'error')
                return redirect(url_for('new_release', repo_name=clean_name))
        

        release_id = db.create_release(clean_name, tag_name, target_commitish, name, body, is_prerelease=is_prerelease)
        

        upload_dir = os.path.join(DATA_DIR, clean_name, 'releases', str(release_id))
        

        temp_keys = request.form.getlist('uploaded_file_keys')
        if temp_keys:
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            
            temp_dir = os.path.join(DATA_DIR, 'temp_uploads')
            
            for key in temp_keys:
                safe_key = secure_filename(key)
                src_path = os.path.join(temp_dir, safe_key)
                
                if os.path.exists(src_path):

                    parts = safe_key.split('_', 1)
                    final_filename = parts[1] if len(parts) > 1 else safe_key
                    
                    dest_path = os.path.join(upload_dir, final_filename)
                    

                    shutil.move(src_path, dest_path)
                    

                    size = os.path.getsize(dest_path)
                    mimetype, _ = mimetypes.guess_type(dest_path)
                    if not mimetype: mimetype = 'application/octet-stream'
                    
                    db.add_release_asset(release_id, final_filename, mimetype, size, dest_path)


        files = request.files.getlist('assets')
        if files:
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
                
            for file in files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(upload_dir, filename)
                    file.save(file_path)
                    

                    size = os.path.getsize(file_path)
                    

                    db.add_release_asset(release_id, filename, file.content_type, size, file_path)
        
        flash('发布版本创建成功', 'success')
        return redirect(url_for('view_releases', repo_name=clean_name))
        
    return render_template('new_release.html', repo_name=clean_name, tags=tags)

@app.route('/<repo_name>/releases/delete/<int:release_id>', methods=['POST'])
@require_auth
def delete_release_route(repo_name, release_id):
    """删除发布版本"""
    clean_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name
    

    release = db.get_release(release_id)
    if not release or release['repo_name'] != clean_name:
        abort(404)
        

    asset_paths = db.delete_release(release_id)
    for path in asset_paths:
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass
    

    release_dir = os.path.join(DATA_DIR, clean_name, 'releases', str(release_id))
    if os.path.exists(release_dir):
        try:
            shutil.rmtree(release_dir)
        except:
            pass
            
    flash('发布版本已删除', 'success')
    return redirect(url_for('view_releases', repo_name=clean_name))

@app.route('/<repo_name>/releases/assets/<int:asset_id>/<filename>')
def download_asset(repo_name, asset_id, filename):
    """下载资产"""
    clean_name = repo_name[:-4] if repo_name.endswith('.git') else repo_name
    
    asset = db.get_asset(asset_id)
    if not asset: abort(404)
    

    if asset['name'] != filename:
        abort(404)
        
    if os.path.exists(asset['path']):
        return send_file(asset['path'], as_attachment=True, download_name=asset['name'])
    else:
        abort(404)

if __name__ == '__main__':
    import socket
    

    def get_local_ips():
        ips = []
        try:

            hostname = socket.gethostname()

            for info in socket.getaddrinfo(hostname, None):
                ip = info[4][0]

                if ':' not in ip and not ip.startswith('127.'):
                    if ip not in ips:
                        ips.append(ip)
        except:
            pass
        

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            if local_ip not in ips and not local_ip.startswith('127.'):
                ips.append(local_ip)
        except:
            pass
            
        return ips
    
    local_ips = get_local_ips()
    
    print("=" * 70)
    print(f"\n📍 本地访问地址:")
    print(f"   http://localhost:{PORT}")
    print(f"   http://127.0.0.1:{PORT}")
    
    if local_ips:
        print(f"\n🌐 局域网访问地址 (同一网络内的其他设备可访问):")
        for ip in local_ips:
            print(f"   http://{ip}:{PORT}")
    
    print(f"\n💡 提示:")
    print(f"   1. 局域网访问: 确保防火墙允许端口 {PORT}")
    print(f"   2. 公网访问: 需要配置路由器端口转发 {PORT} -> 本机")
    print(f"   3. WSL2用户: 可能需要配置端口代理")
    

    try:
        with open('/proc/version', 'r') as f:
            if 'microsoft' in f.read().lower():
                print(f"\n⚠️  检测到 WSL2 环境，外部访问需要额外配置:")
                print(f"   在 Windows PowerShell (管理员) 中运行:")
                if local_ips:
                    print(f"   netsh interface portproxy add v4tov4 listenport={PORT} listenaddress=0.0.0.0 connectport={PORT} connectaddress={local_ips[0]}")
                else:
                    print(f"   netsh interface portproxy add v4tov4 listenport={PORT} listenaddress=0.0.0.0 connectport={PORT} connectaddress=<WSL_IP>")
                print(f"   \n   查看端口转发:")
                print(f"   netsh interface portproxy show all")
                print(f"   \n   删除端口转发:")
                print(f"   netsh interface portproxy delete v4tov4 listenport={PORT} listenaddress=0.0.0.0")
    except:
        pass
    
    print("\n" + "=" * 70)
    print("按 Ctrl+C 停止服务器")
    print("=" * 70 + "\n")
    
    app.run(host='0.0.0.0', port=PORT, threaded=True)
