# AI-Runtime — Claude Code Marketplace

AI-Runtime 是一个外挂式项目知识管理系统，为 Claude Code 提供 GitNexus + Graphify 双引擎知识构建、测试覆盖缺口分析和结构化重构工作流。

## 安装

**方式一：从官方 Marketplace 安装（推荐）**

```
/plugin install ai-runtime
```

**方式二：添加自建 Marketplace 后安装**

```
/plugin marketplace add github:952079739/ai-runtime
/plugin install ai-runtime
```

## 环境要求

- Git、Node.js、npm
- Docker（用于 Qdrant 向量数据库）
- Python 3.11+（需要 `pip install` 安装依赖包）

## 功能

- **SessionStart hook**：自动检测环境、识别项目、报告状态
- **`/bootstrap`**：初始化项目的知识基础设施，配置 LLM 后端，执行首次全量构建
- **`/manage-runtime`**：构建决策（全量/增量）+ 结构化重构工作流（snapshot → patch → changelog）
- **`/test-gap`**：发现高影响但零测试覆盖的符号

## 快速开始

```bash
cd your-project
claude
# SessionStart 报告："New project detected. Run /bootstrap to initialize."
/bootstrap
# 跟随引导完成初始化...
```

## 项目结构

```
ai-runtime-plugin/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace 清单
├── plugins/
│   └── ai-runtime/
│       ├── .claude-plugin/
│       │   └── plugin.json       # 插件元数据
│       ├── package.json
│       ├── hooks/                # SessionStart 生命周期钩子
│       ├── skills/               # bootstrap / manage-runtime / test-gap
│       └── templates/            # runtime-template（脚本、配置、CLAUDE.md）
└── README.md
```
