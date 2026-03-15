# skills 目录

每个子目录对应一个独立的 Skill，推荐结构如下：

```
skills/
└── <skill-slug>/
    ├── SKILL.md        # Skill 能力描述（OpenClaw 标准格式，含 frontmatter）
    ├── _meta.json      # 元数据：slug、版本、publishedAt 等
    ├── USAGE.md        # 配置与使用说明
    ├── references/     # 设计文档、调研报告、API 说明、使用示例等
    └── scripts/        # 实现脚本（Python / Shell 等）
```

## 当前 Skills

| 目录 | 名称 | 版本 | 描述 |
|------|------|------|------|
| [a-stock-monitor](a-stock-monitor/SKILL.md) | A 股量化监控 | 0.0.1 | 7 维市场情绪评分、短线/中长线智能选股、实时 Web 监控 |

## 新增 Skill 指引

1. 在 `skills/` 下创建新目录，以 skill slug 命名（如 `my-new-skill`）。
2. 在目录内创建 `SKILL.md`，遵循 OpenClaw Skill 的 frontmatter 格式：
   ```yaml
   ---
   name: my-new-skill
   description: 一句话描述 Skill 能力
   metadata:
     openclaw:
       requires:
         bins: ["python3"]
         packages: ["some-package"]
   ---
   ```
3. 添加 `_meta.json` 记录 slug 与版本：
   ```json
   { "slug": "my-new-skill", "version": "1.0.0" }
   ```
4. 在 `scripts/` 中放入实现脚本，在 `USAGE.md` 中写明配置与使用步骤。
5. 在本文件的「当前 Skills」表格中登记新 Skill。
