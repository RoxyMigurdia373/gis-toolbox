# 网页先行、桌面封装

- 工具业务逻辑、页面和样式以 `config/web_sources.json` 所列网页仓库为源。新增功能先在网页测试，通过功能/文件导出回归和验收后才封装桌面版。
- 桌面专属改动仅涉及窗口、链接打开、运行环境、打包与版本发布。不得仅修改 tools 副本而遗漏网页源码。
- 同步前确认网页源提交已验收，更新 config/web_sources.json 中的明确 commit，再运行 scripts/sync_web_tools.py --apply（自动校验备份），最后 --check 和相关测试。
- 已回退功能、NDVI、GEE 不纳入同步。预发布限制必须在 CHANGELOG.md、VALIDATION.md 和 GitHub Release 说明。
- 不覆盖已有 Git 标签和发布附件；每次变更保存可校验备份。网页新功能不因自动部署而自动晋升桌面稳定版。
