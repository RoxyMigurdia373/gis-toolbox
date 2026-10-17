"""导入坐标格式转换器的已完成静态页面，不添加未完成的功能。"""
import json
from pathlib import Path
import re
import subprocess


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    source = root.parent / 'coordinate-converter'
    target = root / 'tools' / 'coordinate_converter'
    if target.exists():
        raise FileExistsError('目标已存在，不覆盖坐标转换器')
    page = (source / 'index.html').read_text(encoding='utf-8')
    style = re.search(r'<style>(.*?)</style>', page, re.S)
    script = re.search(r'<script>(.*?)</script>', page, re.S)
    if not style or not script:
        raise ValueError('未找到静态页面样式和脚本')
    target.mkdir(parents=True)
    (target / 'style.css').write_text(style[1].strip() + '\n', encoding='utf-8')
    (target / 'app.js').write_text(script[1].strip() + '\n', encoding='utf-8')
    page = page.replace(style[0], '<link rel="stylesheet" href="style.css">').replace(
        script[0], '<script src="app.js"></script>')
    (target / 'index.html').write_text(page, encoding='utf-8')
    data = dict(id='coordinate_converter', name='坐标转换计算器',
                description='度分秒、十进制度、度分互转，自动推荐 UTM 与 CGCS2000 投影分带',
                type='static', entry='index.html', icon='assets/icon.png',
                working_dir='tools/coordinate_converter')
    (target / 'manifest.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    (target / 'SOURCE.md').write_text(
        '# 来源\n\n仓库：https://github.com/RoxyMigurdia373/coordinate-converter\n\n'
        f'导入版本：`{commit}`\n\n从当前主分支导入，只有将内联 CSS/JS 拆为本地文件的结构调整。'
        '原有计算逻辑保持。此工具进行坐标表示格式转换与分带推荐，不进行大地基准或投影坐标变换。\n',
        encoding='utf-8')
    print('Imported coordinate_converter at', commit)
