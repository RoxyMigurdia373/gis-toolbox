import unittest
from unittest.mock import Mock
from qt_compat import save_download


class DownloadTests(unittest.TestCase):
    def test_qt6_save_chinese_filename(self):
        download = Mock()
        save_download(download, 'C:/output/中文结果.zip')
        download.setDownloadDirectory.assert_called_once_with('C:\\output')
        download.setDownloadFileName.assert_called_once_with('中文结果.zip')
        download.accept.assert_called_once()
        download.setPath.assert_not_called()

    def test_cancel_does_not_accept(self):
        download = Mock()
        save_download(download, '')
        download.cancel.assert_called_once()
        download.accept.assert_not_called()
