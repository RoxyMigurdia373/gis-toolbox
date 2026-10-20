# 网页测试入口与封装规则

| 工具 | 网页测试入口 |
| --- | --- |
| 耕地地块周边地物分析 / 字段配色 | https://farmland-osm-roxy.streamlit.app/ |
| SHP 转 KML / KMZ / GeoJSON 转 SHP | https://shp2kml-nb5tmpnlrpxxmmwvgobcka.streamlit.app/ |
| 按文件大小切分矢量数据 | https://vector-size-splitter-roxy.streamlit.app/ |
| 坐标转换计算器 | https://roxymigurdia373.github.io/coordinate-converter/ |

网页用于功能开发和测试；云端文件上传到托管服务器处理。Community Cloud 休眠时可点击唤醒。桌面版仅导入验收通过的明确源提交，在本机离线处理。

1. 在对应网页仓库修改代码、更新测试及 CHANGELOG，保留备份标签。
2. 验证网页可打开、真实样例可转换并下载，测试错误输入与原有功能；确认成熟。
3. 更新桌面 config/web_sources.json 的已验收提交；不得将未验收测试功能直接打包。
4. 运行 `python scripts/sync_web_tools.py --apply`，自动校验源工作区、提交和备份，再导入明列的文件。
5. 运行 `--check`，检查四个工具代码及来源哈希；运行相关回归，再按照 RELEASES.md 构建、验证及发布新版本。

同步脚本不会推送远端、发布软件、修改桌面依赖或删除文件；新增依赖需另行评估打包兼容性，旧版本标签和附件不得覆盖。
