# TASKS（自动维护）
- 规则：遵循"顶层 ≤1h 粒度；运行中问题以缩进子任务新增；完成后附证据"。

[S1｜完成度 20%]

基于PLAN.md的分析，需要完成以下任务：

- [x] Task-1: 创建项目基础结构
    - 要求：建立Python项目标准目录结构，创建pyproject.toml配置文件
    - 说明：创建src目录结构，配置项目依赖和入口点
    - 测试：检查项目结构是否完整，配置文件是否正确
    - 证据：pyproject.toml、src/dropbox_link_generate/、tests/

- [x] Task-2: 实现Dropbox API集成模块
    - 要求：创建Dropbox API客户端，实现文件共享功能
    - 说明：使用官方Dropbox API SDK，实现文件的共享链接生成和管理
    - 测试：测试API连接和基本功能
    - 证据：src/dropbox_link_generate/services/dropbox_client.py、tests/test_client_url.py

- [x] Task-3: 实现路径校验逻辑
    - 要求：验证文件路径是否在Dropbox目录下，处理符号链接
    - 说明：实现路径规范化和校验逻辑，处理边界情况
    - 测试：测试各种路径情况的校验
    - 证据：src/dropbox_link_generate/utils/paths.py、tests/test_paths.py

- [x] Task-4: 实现CLI命令行界面
    - 要求：创建dplk命令行入口，处理参数解析
    - 说明：使用argparse或click实现命令行界面，支持必要参数
    - 测试：测试CLI参数解析和基本交互
    - 证据：src/dropbox_link_generate/cli.py、pyproject.toml [project.scripts]

- [x] Task-5: 实现共享链接生成和管理
    - 要求：实现文件的共享链接创建、查询和复用逻辑
    - 说明：集成Dropbox API，实现幂等的链接生成
    - 测试：测试链接创建和复用功能
    - 证据：src/dropbox_link_generate/core/sharing.py、services/dropbox_client.py

- [x] Task-6: 实现剪贴板复制功能
    - 要求：自动将生成的链接复制到系统剪贴板
    - 说明：使用pyperclip库实现跨平台剪贴板操作
    - 测试：测试剪贴板复制功能
    - 证据：src/dropbox_link_generate/utils/clipboard.py（CLI默认自动复制，测试中已打桩）

- [x] Task-7: 添加错误处理和日志记录
    - 要求：实现统一的错误处理和可选的日志记录
    - 说明：处理网络错误、API错误等，提供友好的错误信息
    - 测试：测试各种错误情况的处理
    - 证据：utils/errors.py、utils/logging.py、CLI统一非零退出码

- [x] Task-8: 创建配置文件支持
    - 要求：支持.env配置文件，读取DROPBOX_TOKEN和DROPBOX_ROOT
    - 说明：实现配置文件加载和验证
    - 测试：测试配置文件的读取和验证
    - 证据：.env.example、utils/config.py、tests/test_config.py

- [x] Task-9: 编写测试用例
    - 要求：为各个模块编写单元测试和集成测试
    - 说明：确保代码质量和功能正确性
    - 测试：运行测试套件
    - 证据：tests/ 全部通过（13 passed）

- [x] Task-10: 创建使用文档和README
    - 要求：编写项目README和使用说明
    - 说明：提供安装、配置和使用指南
    - 测试：验证文档的完整性和准确性
    - 证据：README.md（安装、配置、用法、选项）
