# dpjf 短视频教练技能包

主路由：`/dpjf`。所有技能和资料都在本目录 `12_skill/dp-jf/`，没有另一套 `dojf` 包。

## 怎么找

| 位置 | 用途 |
|---|---|
| `skills/dpjf/` | 主路由、任务状态恢复、子技能发现、组合和交接 |
| `skills/dpjf-*/` | 15个子技能：独立专业判断、资源调用、场景、案例及交付规则 |
| `共享资源/` | 方法库、补充方法、72变、教学卡片、语料、模板和共同规则 |
| `scripts/` | 语料检索、文本检查、清单与本地打包脚本 |
| `tests/`、`evals/` | 当前结构测试和本地行为评测记录 |
| `维护/` | 更新说明、本地候选清单与已停用的历史资料 |
| `version.json` | 当前版本、状态与更新来源的唯一版本记录 |
| `SKILL.md` | 旧 `dp-jf` 安装路径的兼容转发，不是第二套方法 |

本机 `知识卡片库/_素材资源/` 继续保留原有素材制作任务及文件路径，不进入安装包。**技能包不内置 `学员/` 文件夹**；首次使用时由用户提供学员资料父目录，再由 `dpjf-student` 建立各学员子文件夹。历史资料里的旧流程和旧题库只作追溯，不是当前执行规则。

## 子技能

| 命令 | 用途 |
|---|---|
| `/dpjf-plan` | 账号定位、主页与获客规划 |
| `/dpjf-benchmark` | 对标筛选、作品拆解与迁移 |
| `/dpjf-topic` | 选题开发与筛选 |
| `/dpjf-title` | 标题、封面文字与开头 |
| `/dpjf-script` | 文案创作、诊断与修改 |
| `/dpjf-creative` | 72变、拍法与画面设计 |
| `/dpjf-homework` | 每日作业与教学调整 |
| `/dpjf-review` | 视频评价与优先改进 |
| `/dpjf-communication` | 学员沟通和退款投诉分诊 |
| `/dpjf-patrol` | 多学员巡检与优先级 |
| `/dpjf-recap` | 阶段复盘与单变量调整 |
| `/dpjf-growth` | 自然放大与投流前判断 |
| `/dpjf-learning` | 概念、方法论与研究型学习 |
| `/dpjf-student` | 学员建档、钉钉证据和文件路径闸门 |
| `/dpjf-update` | 本地版本和技能包更新 |

共享资料说明见 `共享资源/规则/来源与取用.md`，主责覆盖见 `共享资源/规则/资源索引.json`。运行 `python skills/dpjf/scripts/list-skills.py` 可检查15个子技能的发现情况。

## 安装与更新

```bash
npx -y skills add sud981953-netizen/dp-jf -g --all --full-depth
```

也可以直接说“更新 dp-jf”。更新前会核对本地改动、学员资料和回退点，详见 `维护/更新说明.md`。当前发布版本为 **3.1.2**。安装后如新对话未显示技能，请重新打开会话。

更新验证成功后，如需只保留最新版，先预览再清理旧版：

```bash
python scripts/cleanup_old_versions.py --current-root "<最新版技能包目录>"
python scripts/cleanup_old_versions.py --current-root "<最新版技能包目录>" --apply
```

清理仅限 dp-jf、dpjf-*、dojf* 及对应旧备份，不触及其他技能、学员资料或未知文件。
