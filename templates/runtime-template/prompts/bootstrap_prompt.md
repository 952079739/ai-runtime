请初始化当前仓库的 AI Runtime。

必须严格使用：

<plugin_dir>/templates/runtime-template

作为唯一 Runtime SDK。

禁止：

- 在 Git 仓库内创建 Runtime
- 污染 Git 仓库
- 修改 Runtime 架构
- 修改 graph schema
- 修改 context schema

必须：

1. 自动读取：

- git remote
- current branch

2. 自动生成：

ProjectID = {repo_name}_{md5_hash_8chars}

3. 自动检查：

{storage_root}/projects/{ProjectID}

是否存在。

存在：

- 复用 Runtime
- 复用 graph
- 复用 embeddings
- 复用 context

不存在：

- 运行 runtime_bootstrap.py 创建完整 Runtime

4. 所有知识必须写入：

{storage_root}/projects/{ProjectID}

5. 初始化完成后：

执行：

full_build.ps1 (Windows) 或 full_build.sh (Mac/Linux)

6. 后续默认：

incremental build mode。

---

## Runtime 目录结构

```
{storage_root}/projects/{ProjectID}/
├── config/runtime.json          # 项目配置（source_path, git_remote, branch...）
├── knowledge/
│   ├── context.md               # 自动生成的项目上下文（Claude 读取入口）
│   ├── architecture/            # 架构分析
│   └── global-graph/            # 依赖图
├── logs/
│   ├── build/                   # 每次 build 的日志
│   ├── graph/                   # graph 构建日志
│   ├── claude/                  # Claude 交互日志
│   └── runtime/                 # runtime 元数据日志
├── tasks/
│   ├── active/                  # 进行中的任务
│   ├── completed/               # 已完成
│   └── failed/                  # 失败的
├── patches/                     # 每次修改的 git diff 补丁
├── snapshots/                   # 大改前自动快照
├── changelog/                   # 变更记录
└── scripts/                     # 工作流脚本
```

---

## Claude 重构工作流

接到重构任务时，Claude 自动执行：

```
1. task.py create "目标" "约束1" "约束2"
   → tasks/active/task_xxx.md

2. snapshot.py "改动说明"
   → snapshots/xxx.patch（保存当前状态）

3. [执行代码修改]

4. patch.py "改动描述" "说明"
   → patches/xxx.patch（保存 diff）

5. changelog.py "标题" "文件列表" "原因" "兼容性"
   → changelog/xxx.md

6. incremental_build.ps1 (Windows) 或 incremental_build.sh (Mac/Linux)
   → 重建 graph + context + 写日志

7. task.py complete task_xxx
   → tasks/completed/
```

所有产物在 {storage_root}/projects/{ProjectID}/ 下，Git 仓库零污染。
