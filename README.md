# Olsc_GitWeb

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python-Version](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![Flask-Version](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)

**Olsc_GitWeb** 是一个轻量级、自托管的 Git 仓库 Web 管理器。它旨在提供一个类似 GitHub 的简洁界面，支持 Git 智能 HTTP 协议，让您能够轻松地在任何设备上通过浏览器管理和浏览您的 Git 项目。

---

## 🌟 核心特性

- 🖥️ **类 GitHub UI**: 极致简约且现代的界面风格，支持深色模式逻辑。
- 📦 **Git 协议支持**: 
  - 支持 **Git Smart HTTP** 协议（支持 `git clone`, `git push`, `git pull`）。
  - 支持 **Git Dumb HTTP** 协议作为备份。
- 🔍 **项目浏览器**:
  - **文件树导航**: 直观的分级目录结构。
  - **代码高亮**: 自动识别并渲染常见编程语言（通过浏览器端 Prism.js 或类似方案）。
  - **Markdown 渲染**: 完美支持 `README.md` 预览（支持表格、代码块等）。
- 📜 **提交历史 & 差异对比**:
  - 详细的提交记录列表。
  - 交互式的提交差异 (Diff) 查看。
  - 支持比较任意两个分支或标签（Compare）。
- 🌿 **引用管理**:
  - 分支列表查看与状态跟踪。
  - 标签列表管理。
- ⚙️ **仓库管理**:
  - 在线创建/物理删除仓库。
  - 编辑仓库元数据（描述、主要语言标签）。
- 🔐 **安全认证**:
  - 基于 `key.txt` 的简单哈希身份验证，保障您的私有仓库安全。

## 🛠️ 技术栈

- **后端**: [Python 3](https://www.python.org/) + [Flask](https://flask.palletsprojects.com/)
- **数据库**: [SQLite3](https://www.sqlite.org/index.html) (用于存储仓库元数据)
- **Git 引擎**: 原生 [Git CLI](https://git-scm.com/) (通过 `subprocess` 调用)
- **前端库**:
  - [Marked.js](https://marked.js.org/): 客户端 Markdown 解析。
  - [Font Awesome](https://fontawesome.com/): UI 图标支持。
  - [GitHub Markdown CSS](https://github.com/sindresorhus/github-markdown-css): 还原经典的 GitHub 文档样式。

## 🚀 快速开始

### 1. 前置要求
确保您的系统已安装：
- Python 3.7+
- Git (并确保 `git` 命令在系统路径中)

### 2. 安装依赖
```bash
pip install flask markdown
```

### 3. 配置密码
在项目根目录创建 `key.txt` 文件，并写入您的访问密码：
```text
your_secure_password
```
*注：服务器启动时会自动将其转换为 SHA256 哈希存储。*

### 4. 运行服务器
```bash
python web.py
```
默认情况下，服务器将在 `http://0.0.0.0:8080` 运行。

### 5. 网络访问
- **本地访问**: `http://localhost:8080`
- **局域网访问**: 确保防火墙允许 8080 端口，使用本机局域网 IP 访问。
- **WSL2 用户**: 如果在 WSL2 中运行，程序会提示您使用 `netsh` 命令配置端口转发。

## 📂 项目结构

```text
Olsc_GitWeb/
├── data/               # 实际存储 Git 仓库的目录
├── static/             # 静态资源 (CSS, JS, 图标)
├── templates/          # HTML 模板文件
├── db.py               # 数据库处理逻辑
├── web.py              # 主程序入口及路由
├── repos.db            # SQLite 数据库文件 (运行后生成)
├── key.txt             # 身份验证密码文件
└── LICENSE             # 项目授权协议 (AGPL v3)
```

## 🤝 贡献与反馈

如果您在使用过程中遇到任何问题或有新的功能建议，欢迎提交 Issue。

## 📄 开源协议

本项目基于 [GNU Affero General Public License v3.0 (AGPL-3.0)](LICENSE) 开源。这意味着如果您在网络上分发修改后的版本，您必须根据该协议提供完整的源代码。
