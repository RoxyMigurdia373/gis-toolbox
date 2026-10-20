"""pywebview 6.2.1 的 Qt 下载回调仍调用 Qt5 setPath；适配 Qt6 API。"""
from pathlib import Path


def configure_webview_settings(webview):
    webview.settings['ALLOW_DOWNLOADS'] = True
    # Streamlit links use target=_blank. Qt's embedded-popup branch is broken
    # in pywebview 6.2.1; open reference/download sites in the system browser.
    webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = True


def save_download(download, path):
    if not path:
        download.cancel()
        return
    target = Path(path)
    download.setDownloadDirectory(str(target.parent))
    download.setDownloadFileName(target.name)
    download.accept()


def configure_qt_downloads(renderer):
    if renderer != 'qtwebengine':
        raise RuntimeError(f'窗口内核不符合打包配置：{renderer}')
    from webview.platforms import qt

    def on_download_requested(self, download):
        name = Path(download.suggestedFileName().replace('\\', '/')).name or 'download'
        path, _ = qt.QFileDialog.getSaveFileName(self, '保存文件', name, '所有文件 (*)')
        save_download(download, path)

    qt.BrowserView.on_download_requested = on_download_requested
