# -*- coding: utf-8 -*-
"""
paynet 量化仪表盘 - 桌面启动器
启动 Flask 后端 + pywebview 桌面窗口。
- 源码模式：python launcher.py
- 打包模式：PyInstaller 打包后双击 exe
"""
import os, sys, threading, time

PORT = 51888


def start_server():
    from app import app
    # 关闭 reloader，避免在打包/线程里重复启动
    app.run(host='127.0.0.1', port=PORT, debug=False, use_reloader=False)


def wait_for_server(timeout=20):
    import urllib.request
    for _ in range(timeout * 4):
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{PORT}/', timeout=1)
            return True
        except Exception:
            time.sleep(0.25)
    return False


def block_forever():
    """pywebview 不可用时的兜底：保持进程不退出，让浏览器能访问。"""
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        pass


def main():
    t = threading.Thread(target=start_server, daemon=True)
    t.start()

    if not wait_for_server():
        import webbrowser
        webbrowser.open(f'http://127.0.0.1:{PORT}/')
        print('服务未就绪，已尝试用浏览器打开。保持窗口开启。')
        block_forever()
        return

    try:
        import webview
        webview.create_window('paynet 量化仪表盘',
                              f'http://127.0.0.1:{PORT}/',
                              width=1280, height=820,
                              min_size=(960, 600))
        webview.start()
    except Exception as e:
        import webbrowser
        webbrowser.open(f'http://127.0.0.1:{PORT}/')
        print(f'pywebview 启动失败({e})，已用浏览器打开。保持窗口开启。')
        block_forever()


if __name__ == '__main__':
    main()
