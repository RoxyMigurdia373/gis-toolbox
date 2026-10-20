# 版本发布与回退

仓库：https://github.com/RoxyMigurdia373/gis-toolbox

每次功能更新前确认上一个稳定版本已有 Git 标签和 GitHub Release，包含 Windows ZIP、源码 ZIP、SHA256SUMS.txt。禁止移动既有标签或替换旧附件。v1.0.0 已建立基线。

每次更新的流程：

0. 功能先在网页源仓库开发、测试和验收；桌面窗口/打包修复在本仓库处理。更新 config/web_sources.json 中已验收源提交，运行 `scripts/sync_web_tools.py --apply` 自动备份并导入，然后 `--check` 确认无差异。不得自动将网页测试中功能晋升桌面稳定版。

1. 更新 `config/app_config.toml` 版本号、README、CHANGELOG 和 VALIDATION，写清新增功能、已知限制及验证结果。
2. 运行相关测试并检查界面。提交全部源码变更。
3. 运行 `.venv\Scripts\python.exe scripts/build_desktop.py`。构建前自动在项目同级 `gis-toolbox-backups/before-build-时间戳/` 备份当前源码、现有 dist；任一备份或校验失败即中止，不清理旧程序。
4. 验证打包程序，必要的修复重新提交并重新构建。
5. 运行 `.venv\Scripts\python.exe scripts/make_release.py`。仅接受干净 Git 工作区，并检查构建版本号；输出到 `release/v版本号/`，已有目录则拒绝执行。失败后保留残留文件供检查，人工另存后再重试，不自动覆盖。
6. 为已验证提交建立新的 `v版本号` 标签，推送 main 和该标签；在 GitHub 建立同名 Release，按 CHANGELOG 编写说明并上传三个附件。尚未验证完成的版本使用预发布标记，不宣称稳定版。
7. 核对远端附件名称、大小和 SHA256，与本地一致后交付。

回退：从对应 Release 下载旧 Windows ZIP，解压到新的独立目录后运行；不要将不同版本的 `_internal` 合并。用户下载的输出文件不放在程序目录中。开发源码可在独立 worktree 检出旧标签，不重置或删除当前未提交工作。

备份目录独立于项目，不纳入 Git。不要将虚拟环境、工作数据、日志、构建目录和 Windows 大包直接提交到 Git 历史；大包通过 Releases 分发。
