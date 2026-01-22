# Olsc_GitWeb 🚀

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python-Version](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![Flask-Version](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![SQLite-Version](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Git-CLI](https://img.shields.io/badge/Git-CLI-F05032?logo=git&logoColor=white)](https://git-scm.com/)

**Olsc_GitWeb** 是一个轻量级、自托管的 Git 仓库 Web 管理器。它旨在提供一个极具现代感、类似 GitHub 的简洁界面，全面支持 Git 智能 HTTP 协议，让您能够像使用商业云服务一样轻松地管理和托管您的私有 Git 项目。

---

## ✨ 核心特性

### 🎨 卓越的视觉体验
- **类 GitHub UI**: 深度致敬 GitHub 的 UI 设计，提供极致简约且现代的界面。
- **自适应设计**: 完美适配桌面端、平板及手机移动端。
- **深色模式逻辑**: 为您的护眼需求量身打造。

### 📦 强大的 Git 托管功能
- **智能 HTTP 协议**: 完美支持 `git clone`, `git push`, `git pull` 等原生命令。
- **协议兼容性**: 支持 Git Smart HTTP 规范，并具备 Dumb HTTP 备份支持。
- **ZIP 下载**: 支持一键打包下载仓库任意分支/引用的源代码。

### 🔍 深度交互与浏览
- **文件树导航**: 直观的分级目录结构，支持大文件自动截断优化。
- **多媒体预览**: 在线预览图片、视频、PDF 及常见文档。
- **代码高亮**: 引入现代语法高亮引擎，支持百余种编程语言。
- **Markdown 渲染**: 完美支持 `README.md`（含表格、公式、任务列表）。

### 🛠️ 仓库管理与分析
- **引用管理**: 分支与标签（Branch/Tag）的创建、切换及物理删除。
- **提交记录 (Commits)**: 详细的历史记录轨道，支持通过相对时间展示。
- **对比与差异 (Diff & Compare)**: 交互式 Diff 视图，支持任意两个节点间的 Compare 分析。
- **全局搜索**: 强大的搜索引擎，可同时检索仓库名、代码内容及提交说明。

### 🔐 简易安全
- **零配置认证**: 基于 `key.txt` 的极简 SHA256 哈希身份验证。
- **数据库元数据**: 使用 SQLite3 维护仓库描述、标签等附加信息。

---

## 🛠️ 技术栈

- **后端**: [Python 3](https://www.python.org/) + [Flask](https://flask.palletsprojects.com/) (内核驱动)
- **数据库**: [SQLite3](https://www.sqlite.org/) (元数据持久化)
- **Git 引擎**: 原生 [Git CLI](https://git-scm.com/) (通过 subprocess 高效调用)
- **前端生态**:
  - [Prism.js](https://prismjs.com/): 现代语法高亮。
  - [Marked.js](https://marked.js.org/): 极速 Markdown 解析。
  - [Font Awesome](https://fontawesome.com/): 矢量图标支持。
  - [GitHub Markdown CSS](https://github.com/sindresorhus/github-markdown-css): 工业级文档渲染。

---

## 🚀 快速启动

### 1. 前置准备
确保您的运行环境已安装 **Python 3.7+** 和 **Git CLI**。

### 2. 克隆与安装
```bash
# 克隆本项目
git clone https://github.com/your-repo/Olsc_GitWeb.git
cd Olsc_GitWeb

# 安装必要依赖
pip install flask markdown
```

### 3. 配置安全密钥
在项目根目录创建 `key.txt`，写入您的初始管理员密码：
```text
my_awesome_password
```
*提示：初次运行后，系统将自动对明文密码进行 SHA256 哈希加密存储。*

### 4. 启动服务
```bash
python web.py
```

### 5. 多路径访问
- **本地控制台**: `http://localhost:8080`
- **局域网协同**: 程序启动时会自动显示为您分配的局域网 IP（如 `http://192.168.x.x:8080`）。
- **WSL2 用户**: 如果您在 WSL2 环境下运行，程序会贴心地提供 `netsh` 端口转发命令建议。

---

## 📂 项目架构

```text
Olsc_GitWeb/
├── data/               # Git 仓库实际存储物理路径 (仓库根目录)
├── static/             # 静态资源库 (CSS 样式、JS 逻辑、图片)
├── templates/          # Jinja2 视图模板 (GitHub 风格 HTML)
├── db.py               # 数据库 ORM 层 (Sqlite3 交互)
├── web.py              # 项目路由枢纽与核心控制器
├── repos.db            # 自动生成的元数据库
├── key.txt             # 身份验证令牌凭证
└── LICENSE             # AGPL v3 开源协议
```

---

## ⚙️ 进阶配置

### 克隆您的仓库
在另一台机器上，您可以使用如下 URL 进行克隆：
```bash
git clone http://your-server-ip:8080/my-project.git
```

### 环境变量
可以通过修改 `web.py` 中的 `PORT` (默认 8080) 来自定义服务端口。

---

## 🤝 贡献与反馈

欢迎提交 Issue 或 Pull Request 来完善 Olsc_GitWeb！我们尤其欢迎关于 UI 优化和新 Git 特性的建议。

## 📄 开源协议

本项目基于 **[GNU Affero General Public License v3.0 (AGPL-3.0)](LICENSE)** 协议开源。在分发任何修改后的版本时，请务必保持代码的开源属性并注明原作者。
