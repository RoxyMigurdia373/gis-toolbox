# 可选的 GDAL 命令行包

默认不需要：SHP 转换工具已内置 Fiona + PyProj 备用流程。

如需要打包 ogr2ogr，将同一套可再分发的 GDAL CLI 运行环境整理为：

```text
vendor/gdal/
  ogr2ogr.exe
  gdal*.dll、proj*.dll、geos*.dll 及该发行版的全部其他依赖 DLL
  gdal-data/    GDAL 数据文件
  proj-data/    PROJ 数据文件，包含 proj.db
  licenses/    对应许可与版权声明
```

也可设置开发机环境变量 `GIS_GDAL_DIR` 指向上述结构，再运行 build.bat。
只复制几个名称匹配的 DLL 通常不够，必须保证传递依赖和数据目录完整。
不要把 QGIS、OSGeo4W、Fiona 等不同发行版的 DLL 拼在一起。
build.spec 将整套 CLI 作为 datas 放入 `_internal/gdal/`，有意与 Python GIS 库隔离。
运行时先使用系统 PATH 中的 ogr2ogr，再使用打包路径；失败时回退至 Fiona。
QGIS 的安装目录不一定在 PATH 中；可在启动前把对应 bin 加入 PATH。
