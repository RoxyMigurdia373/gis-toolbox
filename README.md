# GIS 工具箱 · Windows 本地桌面版

版本 **1.1.0-rc.2（预发布）**。把已经完成的网页工具放进独立的原生 Windows 窗口，支持同时使用，共享一套内置 Python/GIS 运行环境。

## 当前收录的四个工具

| 工具 | 功能 | 运行方式 |
| --- | --- | --- |
| 耕地地块周边地物分析 | 提取 OSM 材料、最近距离、范围汇总、几何修复、中心经纬度、GeoJSON/SHP 导出 | 独立 Streamlit 进程 |
| 按文件大小切分矢量数据 | GeoJSON/SHP/GPKG 分片、类型与属性检查、可选坐标转换、ZIP 和清单 | 独立 Streamlit 进程 |
| SHP 转 KML / KMZ | 批量转换、中文编码、坐标系处理、结果下载 | 独立 Streamlit 进程 |
| 坐标转换计算器 | 度分秒/十进制度/度分互转、复制结果、UTM 与 CGCS2000 分带推荐 | 本地 HTML，无进程、无端口 |

**不包含 NDVI、GEE 在线分析以及已经回退的功能。** 坐标计算器只转换经纬度表示格式并推荐分带，不进行基准转换或经纬度→投影 XY 计算。坐标页源自用户提供的 [coordinate-converter](https://github.com/RoxyMigurdia373/coordinate-converter)，确切提交记录在 `tools/coordinate_converter/SOURCE.md`。

## 交给同事使用

1. 拷贝整个 `dist/GISToolbox/` 文件夹到同事电脑，可压缩后发送、解压使用。
2. 双击其中的 **GISToolbox.exe**，不要单独拷贝 exe；必须保留 `_internal`。
3. 主界面点击“打开工具”，每个工具在独立窗口打开；再次点击会切换到已有窗口。
4. 用各工具中的下载按钮保存结果。关闭单个窗口只结束该工具；关闭主界面结束所有工具。

支持 Windows 10/11 x64。完整解压后运行 GISToolbox.exe，保留同目录的 _internal 文件夹。内置 Python、GIS 库和 Qt WebEngine，无需另装 Python、QGIS、.NET 或 WebView2。尚未在干净 Windows 虚拟机上验收，企业策略、驱动和系统差异仍可能影响运行。

页面由 Qt WebEngine 嵌入原生窗口；Streamlit 只监听 `127.0.0.1`，不对局域网开放。分析本地处理，遥测关闭。数据不上传云端；若主动点击网页中的外部链接，需要联网。

## 项目结构

```text
gis-toolbox/
  launcher.py                 主入口、freeze_support、单实例锁、Qt WebEngine
  main_window.py              主窗口与有限 JS API
  tool_manager.py             注册工具的窗口与进程生命周期
  port_allocator.py           8501–8600 优先端口和动态回退
  resource_utils.py           资源路径、用户目录、锁、ogr2ogr 查找
  process_job.py              Windows Job Object，回收服务的子进程
  logger.py                   轮转日志
  manifest_loader.py          扫描和校验 manifest
  config/app_config.toml      名称、版本、尺寸、端口、启动超时
  ui/                        主界面 HTML/CSS/JS
  tools/
    farmland_context/         耕地周边分析当前代码副本
    split_by_size/            矢量分片当前代码副本
    shp_to_kml/               SHP 转换当前代码副本
    coordinate_converter/     坐标计算器当前静态页面
  .streamlit/config.toml      通用 Streamlit 配置
  requirements.txt           按需求锁定的全部直接依赖
  constraints.txt            PyArrow 间接依赖兼容性约束
  requirements-dev.txt       附加测试依赖
  build.spec / build.bat      Windows onedir 构建
  icon.ico                   应用图标
  add_tool.py                交互式导入新工具
  scripts/                   初始导入、图标生成、构建辅助脚本
  tests/                     容器生命周期测试
  vendor/README.md           可选 GDAL CLI 打包说明
```

四个工具均有自己的 `manifest.json` 与图标。`prepare_tools.py`/`import_coordinate.py` 是一次性整合脚本，已有目标时会拒绝覆盖，日常运行/打包不需要执行。

## 开发运行

开发机推荐 Python **3.11 x64**，也支持 3.12；当前构建环境使用 Python 3.12 x64。以下 PowerShell 命令在项目根目录执行：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe launcher.py
```

已激活环境后也可执行 `python launcher.py`。若电脑只有 3.12，把首行改成 `py -3.12 -m venv .venv`。本项目环境与原来三个网页项目的环境分开，原目录没有被修改。

所有指定的直接依赖版本均保持。额外通过 `constraints.txt` 固定 `pyarrow==19.0.1`：Streamlit 没有限制 PyArrow 上界，2026 年最新版 PyArrow 要求 NumPy 2，而本项目明确使用 NumPy 1.26.4。不要删除该约束。

桌面副本对原工具的改动限于容器兼容：Streamlit 1.40.1 的表格使用 `use_container_width=True`；下载按钮不使用新版才支持的 `on_click="ignore"`；SHP 转换新增打包 GDAL 路径、隐藏 CLI 窗口和失败日志。分析算法保持现有版本。

## 打包

双击 **build.bat**。它会创建 `.venv`（优先 3.11，回退 3.12）、安装锁定依赖、清理项目自己的 `build`/`dist` 后运行 PyInstaller。**重新构建前自动备份源码和现有 dist 到同级 gis-toolbox-backups，校验成功后才替换构建目录。**

也可手动执行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/build_desktop.py
```

输出为 `dist/GISToolbox/GISToolbox.exe`。使用 `COLLECT/onedir`，`console=False`，`upx=False`，所有工具共享内置解释器和 GIS DLL。pywebview 的实际导入包名是 `webview`，spec 按此收集资源、Qt WebEngine（PySide6）；排除 Python.NET/CLR 和 WinForms 后端。

`tools` 中的缓存、`.git`、`.venv`、测试日志不打进安装目录。开发机安装依赖和构建需要联网；同事运行四个本地工具不需要联网。

## 添加第 5 个工具

在 `tools/new_tool/` 放入已经完成的代码、`assets/icon.png`，并添加：

```json
{
  "id": "new_tool",
  "name": "新工具",
  "description": "工具简介",
  "type": "streamlit",
  "entry": "app.py",
  "icon": "assets/icon.png",
  "port_preference": 8504,
  "working_dir": "tools/new_tool"
}
```

静态工具设置 `"type": "static"`、`"entry": "index.html"`，去掉 `port_preference`。无需更改主程序，重启开发版即可发现；发布给同事前重新打包。也可执行 `python add_tool.py` 交互式复制与生成 manifest。

新工具若有新的第三方库，需要补充统一 requirements 和 PyInstaller 收集规则。manifest 自动注册不等于自动安装新依赖。静态工具的所有 JS/CSS/图片必须是本地资源，避免 CDN 导致离线不可用。工具代码应使用 `TemporaryDirectory` 处理上传，不能向程序目录写入。

## 进程、端口和文件位置

- 三个 Streamlit 工具优先 8501/8502/8503；冲突时自动在 8501–8600 分配空闲端口。启动探测同时检查服务进程、子进程就绪消息和 `/_stcore/health`，不是只判断端口能连通。
- 静态坐标页使用 `file:///.../index.html`，没有 Python 子进程和 HTTP 端口。
- 正常关闭先通过管道请求 Streamlit 停止，等待后再 terminate/kill；Windows Job Object 清理后代进程。使用管道而非跨进程 Event，避免服务强杀后遗留锁导致父程序卡死。
- 服务意外退出时关闭失效窗口，在卡片显示错误，可重新打开；损坏 manifest 只跳过对应工具并写日志。
- 主窗口退出时会清理全部服务；单个窗口的关闭不影响其他工具。

```text
%APPDATA%/GISToolbox/
  .lock                    操作系统文件锁，异常退出自动释放
  logs/app.log             主程序日志，5 MB 轮转，保留 3 份
  logs/<tool_id>.log        各工具服务日志
  temp/<tool-id>-<随机串>/  每次服务的临时目录，正常关闭清理
  streamlit/               Streamlit 用户配置/凭据路径
  webview/                 Qt WebEngine 缓存与用户配置
```

用户目录不可写时回退到系统 temp 的 `GISToolbox/`。日志入口会打开实际使用的日志目录。断电或强制结束造成的临时目录可能需要手动清理，程序不会误删其他用户数据。下载到哪里由用户在系统保存对话框中选择。

## ogr2ogr / GDAL

转换优先使用系统 PATH 中的 `ogr2ogr`，其次使用 `_internal/gdal/ogr2ogr.exe`，都没有或执行失败时使用内置 **Fiona + PyProj**。缺少 CLI 的提示不会阻止工具运行。

开发机目前没有可用的独立 ogr2ogr，因此默认发行目录使用已验证的 Fiona 备用流程，**不伪装成已经包含 ogr2ogr**。若同事安装了 QGIS/GDAL 并配置相应 bin 到 PATH，会优先使用它；仅安装 QGIS 但没有配置 PATH，不保证自动检测。

可选 CLI 打包：准备完整可再分发的同一版本运行环境放入 `vendor/gdal/`，或设置 `GIS_GDAL_DIR`。spec 会完整复制到 `_internal/gdal/`，包括依赖 DLL、`gdal-data`、`proj-data` 和许可证。详见 [vendor/README.md](vendor/README.md)。不要 pip 安装 GDAL Python 绑定，不要混合不同发行版 DLL。CLI 的 GDAL/PROJ 环境变量只传给对应子进程，不污染 Fiona。

## 验证命令

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pytest tools/split_by_size/tests/test_splitter.py -q
# 可选：开发机装有 Node.js 时验证坐标核心；同事运行应用不需要 Node.js
node tests/test_coordinates.js
```

另外两个工具的原有测试需在各自目录执行，避免同名 `io_utils` 模块冲突：

```powershell
Push-Location tools/farmland_context
..\..\.venv\Scripts\python.exe -m unittest discover -s tests -v
Pop-Location
Push-Location tools/shp_to_kml
..\..\.venv\Scripts\python.exe -m unittest discover -v
Pop-Location
```

## 发布前验收清单

- [ ] 干净的 Windows 10/11 x64、无 Python/QGIS，确认内置 Qt WebEngine 可用。
- [ ] 主界面准确列出四个工具，未包含 NDVI/回退功能。
- [ ] 三个 GIS 工具各完成典型上传、处理和结果下载。
- [ ] 坐标计算器在断网状态可打开，测试格式转换、分带和复制。
- [ ] 四个窗口同时打开，三个服务端口互不冲突。
- [ ] 重复打开聚焦原窗口，关闭一个不影响其他窗口。
- [ ] 主窗口退出后无 GISToolbox 服务残留；开发模式无本次启动的 Python 子进程残留。
- [ ] 缺少 ogr2ogr 时 Fiona 回退成功；若打包了 CLI，另行确认 CLI 真正执行成功。
- [ ] 日志与临时文件位于用户目录，程序目录可设为只读。

本机源码测试和本机 exe 测试不能替代干净虚拟机验收；本项目未自动安装或修改系统组件。

## 常见问题

**首次打开较慢**：GIS DLL、Streamlit 和 Qt WebEngine 初始化可能需 10–20 秒，具体取决于磁盘、杀毒软件和电脑。onedir 运行时不需要像 onefile 一样每次解压。默认服务启动上限 30 秒，可在 config 中调整后重新构建。

**杀毒软件误报**：未签名 PyInstaller 程序可能被误报。应先核对来源和扫描结果，企业分发建议代码签名并提交误报审核；如需白名单请按单位规范由管理员处理，不建议关闭安全软件。

**端口冲突**：自动回退至 8501–8600；全部占用时会提示关闭其他程序。没有端口的静态工具仍可使用。

**启动失败/白屏**：确认使用 Windows 10/11 64 位并完整解压全部文件，不要单独复制 EXE。不要混用不同版本的 _internal。查看 %APPDATA%\GISToolbox\logs\app.log；v1.1.0-rc.2 已移除产生 Python.Runtime.Loader.Initialize 错误的 CLR 启动链。

**ogr2ogr 找不到**：使用 Fiona 备用流程即可；需要 CLI 时使用完整的 QGIS/GDAL 环境并配置 PATH，或按 vendor 文档重新打包。

**GDAL/PROJ DLL 错误**：使用新的独立 venv，确认 collect_all 和标准 PyInstaller hooks 生效。不要把系统 QGIS DLL 复制进 Fiona 包目录。PROJ 数据库必须对应当前发行版。

**下载没有弹框**：本程序已启用 pywebview `ALLOW_DOWNLOADS`。检查保存对话框是否在窗口后面，或查看应用/工具日志。

**再次双击没打开**：单实例锁阻止重复启动，从任务栏切换到已有工具箱。锁文件存在本身不是运行中标志，无需手动删除它。

## 更新说明

1.0.0：整合三个现有 Streamlit 工具与仓库版坐标计算器；新增本地窗口、manifest 注册、端口回退、单实例、日志、进程回收及 onedir 构建。升级时替换整个发布文件夹，用户日志与 WebView 缓存保存在用户目录。

## 1.1 新增工作区

打开“耕地地块周边地物分析”，在侧栏选择“矢量字段配色”。该入口独立处理上传文件，无需先分析耕地。

- 配色：上传 GeoJSON 或 Shapefile ZIP → 查看属性 → 选择字段 → 选择字段值并设置颜色 → 设置线宽与面填充不透明度 → 生成并下载 GeoJSON。输出 WGS84。
- GeoJSON 转 SHP：打开“SHP 转 KML / KMZ”，切换处理方式 → 上传 GeoJSON → 生成并下载 ZIP。不同几何类型分别保存，中文字段对应关系在 ZIP 内的字段映射.json 中。
- 配色使用 SimpleStyle 的 stroke、fill、marker-color 等属性。GeoJSON 本身没有统一显示样式标准；奥维 10.6.2 实机结果：点和面样式可显示，线样式未按 stroke 显示。Shapefile 转换仅保存几何与属性，不携带渲染样式。
- 中国路网：[Geofabrik 中国下载页](https://download.geofabrik.de/asia/china.html)。使用省级 Shapefile ZIP 的道路图层；工具不直接读取 .osm.pbf。仅有 fclass 时按页面说明映射到 highway。

## 版本历史与备份

[GitHub Releases](https://github.com/RoxyMigurdia373/gis-toolbox/releases) 提供各版本源码、Windows 包和校验清单。详见 [更新日志](CHANGELOG.md) 和 [发布与回退流程](docs/RELEASES.md)。发布脚本读取配置版本号，按版本建目录且拒绝覆盖旧发布包。

UI 设计参考 [frontend-design skill](https://github.com/anthropics/skills/tree/main/skills/frontend-design)，见 [设计说明](docs/DESIGN.md)。运行软件不需要安装此 skill。
