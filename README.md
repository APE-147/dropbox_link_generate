# Dropbox Link Generate (dplk)

一个简单易用的命令行工具，用于快速生成 Dropbox 文件的共享链接。

## 功能特性

- 🔗 一键生成 Dropbox 文件共享链接
- 📋 自动复制链接到剪贴板
- ✅ 验证文件是否在 Dropbox 目录中
- 🔄 幂等操作，复用已存在的共享链接
- 🛡️ 安全的错误处理和明确的错误信息
- 📝 可选的详细日志记录
- 📦 若输入目录，自动压缩为 ZIP 后再生成链接

## 安装

### 本地安装

```bash
# 克隆仓库
git clone https://github.com/niceday/dropbox-link-generate.git
cd dropbox-link-generate

# 安装依赖
pip install -e .
```

### 使用 pipx (推荐)

```bash
pipx install dropbox-link-generate
```

## 配置

1. 创建 `.env` 文件（参考 `.env.example`）：

```bash
cp .env.example .env
```

2. 运行 OAuth 授权以获取 refresh token：

```bash
# 方式一：使用交互式命令
dplk auth

# 方式二：提前设置 APP KEY/SECRET 再运行（避免在命令行输入密钥）
export DROPBOX_APP_KEY=your_app_key
export DROPBOX_APP_SECRET=your_app_secret
dplk auth
```

命令将输出需要写入 `.env` 的值：

```env
DROPBOX_APP_KEY=your_app_key
DROPBOX_APP_SECRET=your_app_secret
DROPBOX_REFRESH_TOKEN=your_refresh_token
# 可选：缓存短期访问令牌，SDK 会在缺省时自动刷新
# DROPBOX_ACCESS_TOKEN=your_short_lived_access_token
DROPBOX_ROOT=/Users/your_username/Dropbox
# 可选：用于存放目录压缩包的 Dropbox 内部目录（必须位于 DROPBOX_ROOT 内）
# DROPBOX_ARCHIVE_DIR=/Users/your_username/Dropbox/Archives
```

`DROPBOX_ARCHIVE_DIR` 必须位于 `DROPBOX_ROOT` 之下。当你向 CLI 传入一个目录时，工具会将其压缩成同名 ZIP，移动到该目录后再生成共享链接。

### 获取 Dropbox OAuth 凭据（手动流程）

1. 访问 [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. 创建新应用或选择现有应用，并启用以下权限：`sharing.read`、`sharing.write`、`files.metadata.read`
3. 在「Permissions」页面勾选所需 scope 后保存
4. 进入「Settings」页，启用 `Allow implicit grant` 以及 `Allow PKCE`（推荐）
5. 参照 [OAuth 指南](https://developers.dropbox.com/oauth-guide) 或使用 `dplk auth` 命令生成 refresh token
6. 将 APP key、APP secret 和 refresh token 写入 `.env`

## 使用方法

### 基本用法

```bash
# 生成文件共享链接
dplk /path/to/your/file.txt

# 链接会自动复制到剪贴板并打印到控制台
https://www.dropbox.com/s/abc123/file.txt?raw=1
```

### 高级选项

```bash
# 显示详细日志
dplk --verbose /path/to/file.txt

# 指定日志文件
dplk --log-file /tmp/dplk.log /path/to/file.txt

# 不复制到剪贴板
dplk --no-copy /path/to/file.txt

# 传入目录时会先压缩为 ZIP，再移动到 DROPBOX_ARCHIVE_DIR 后生成链接
dplk /path/to/folder
```

## 错误处理

工具会处理以下错误情况：

- 文件不在 Dropbox 目录中
- 文件不存在或无法访问
- Dropbox API 错误（网络问题、权限问题等）
- 配置缺失或错误

所有错误都会返回非零退出码（1）并提供清晰的错误信息。

## 开发

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/niceday/dropbox-link-generate.git
cd dropbox-link-generate

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式化
black src/
isort src/

# 类型检查
mypy src/
```

### 项目结构

```
dropbox-link-generate/
├── src/dropbox_link_generate/
│   ├── core/           # 核心功能模块
│   ├── services/       # 服务层
│   ├── utils/          # 工具模块
│   ├── plugins/        # 插件模块
│   ├── cli.py          # 命令行入口
│   └── __init__.py
├── tests/              # 测试文件
├── docs/               # 文档
├── data/               # 数据目录（符号链接）
├── pyproject.toml      # 项目配置
├── README.md           # 项目说明
├── .env.example        # 环境变量示例
└── .gitignore          # Git 忽略文件
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
