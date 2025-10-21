# Dropbox Link Generate (dplk)

一个简单易用的命令行工具，用于快速生成 Dropbox 文件的共享链接。

## 功能特性

- 🔗 一键生成 Dropbox 文件共享链接
- 📋 自动复制链接到剪贴板
- ✅ 验证文件是否在 Dropbox 目录中
- 🔄 幂等操作，复用已存在的共享链接
- 🛡️ 安全的错误处理和明确的错误信息
- 📝 可选的详细日志记录

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

2. 编辑 `.env` 文件，添加你的 Dropbox API token：

```env
DROPBOX_TOKEN=your_dropbox_access_token_here
DROPBOX_ROOT=/Users/your_username/Dropbox
```

### 获取 Dropbox API Token

1. 访问 [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. 创建新应用或选择现有应用
3. 在权限设置中启用 `sharing.write` 权限
4. 生成 Access Token

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