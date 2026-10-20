"""Regression for Streamlit target=_blank links in the pinned Qt backend."""
import os
import unittest
from unittest.mock import Mock, patch

from qt_compat import configure_webview_settings


class ExternalLinkTests(unittest.TestCase):
    def test_osm_popup_uses_default_browser_without_replacing_tool(self):
        os.environ['QT_API'] = 'pyside6'
        import webview
        from webview.platforms import qt
        old = dict(webview.settings)
        try:
            configure_webview_settings(webview)
            handler = Mock()
            url = qt.QtCore.QUrl('https://download.geofabrik.de/asia/china.html')
            with patch.object(qt.webbrowser, 'open', return_value=True) as opened:
                accepted = qt.BrowserView.NavigationHandler.acceptNavigationRequest(handler, url, 0, True)
            opened.assert_called_once_with(url.toString(), 2, True)
            self.assertFalse(accepted)
            handler._parent.load_url.assert_not_called()
            self.assertTrue(webview.settings['ALLOW_DOWNLOADS'])
        finally:
            webview.settings.update(old)
