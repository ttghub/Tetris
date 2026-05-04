# Tkinter 游戏截图最佳实践

## 问题现象

使用 `PIL.ImageGrab` 配合 `tkinter` 的 `winfo_rootx/rooty/w/height` 截图时，截取区域与窗口实际内容**偏移**，或包含非客户区（标题栏、阴影、边框），导致截图不准确。

## 根本原因

Windows 的 **DPI 缩放**（高分辨率屏幕 125%/150%）导致 `tkinter` 返回的逻辑坐标与 `ImageGrab` 的物理像素坐标不一致。此外 `winfo_rootx/rooty` 返回的是窗口外框坐标（含标题栏），不是纯客户区。

## 解决方案

### 1. 关闭进程 DPI 缩放

```python
import ctypes
ctypes.windll.user32.SetProcessDPIAware()
```

### 2. 用 Windows API 精确取窗口客户区坐标

```python
from ctypes import wintypes
from PIL import ImageGrab

def get_client_rect(hwnd):
    """获取窗口客户区在屏幕上的精确坐标（无标题栏）"""
    rect = wintypes.RECT()
    ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect))
    pt = wintypes.POINT(0, 0)
    ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return pt.x, pt.y, rect.right, rect.bottom

def grab_window(root):
    """截取 tkinter 窗口的纯客户区"""
    # 通过窗口标题找到句柄
    hwnd = ctypes.windll.user32.FindWindowW(None, root.title())
    # 或者直接用 tkinter 的 frame id（备选）
    if not hwnd:
        hwnd = int(root.frame(), 16)
    x, y, w, h = get_client_rect(hwnd)
    return ImageGrab.grab(bbox=(x, y, x + w, y + h))
```

### 3. 确保窗口已渲染

```python
# 强制 tkinter 完成所有绘制
for _ in range(10):
    root.update()
root.update_idletasks()
time.sleep(0.5)

# 置顶窗口确保不被遮挡
root.attributes('-topmost', True)
root.lift()
root.update()
time.sleep(0.3)

# 截图
img = grab_window(root)
img.save('screenshot.png')
```

## 完整示例

```python
import sys, os, time, ctypes, tkinter as tk
from ctypes import wintypes
from PIL import ImageGrab

ctypes.windll.user32.SetProcessDPIAware()

def get_client_rect(hwnd):
    rect = wintypes.RECT()
    ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect))
    pt = wintypes.POINT(0, 0)
    ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return pt.x, pt.y, rect.right, rect.bottom

def grab_window(root):
    hwnd = ctypes.windll.user32.FindWindowW(None, root.title())
    x, y, w, h = get_client_rect(hwnd)
    return ImageGrab.grab(bbox=(x, y, x + w, y + h))

def screenshot_app(app_create_fn, filename):
    app = app_create_fn()
    app.root.attributes('-topmost', True)
    for _ in range(10):
        app.root.update()
    app.root.update_idletasks()
    time.sleep(1.0)
    app.root.lift()
    time.sleep(0.5)
    img = grab_window(app.root)
    img.save(filename)
    app.root.destroy()
```

## 关键 API 说明

| API | 作用 |
|-----|------|
| `SetProcessDPIAware()` | 禁用 DPI 缩放，使逻辑坐标 = 物理坐标 |
| `FindWindowW(None, title)` | 按窗口标题查找窗口句柄 |
| `root.frame()` | tkinter 内部的窗口 HWND 字符串（备选） |
| `GetClientRect(hwnd, &rect)` | 获取客户区相对尺寸 |
| `ClientToScreen(hwnd, &pt)` | 将客户区 (0,0) 转为屏幕绝对坐标 |
| `ImageGrab.grab(bbox=(x,y,x+w,y+h))` | 截取指定屏幕区域 |

## 预防措施

1. **永远用 Windows API** 取坐标，不要用 `winfo_rootx/rooty`
2. **截图前强制 `update() + sleep()`**，确保 tkinter 完成渲染
3. **截图前 `lift()` + `topmost`**，确保窗口不被遮挡
4. **检查截图边缘颜色**：如果四角不是窗口背景色，说明截到了标题栏/阴影

## 关联标签

`#tkinter` `#截图` `#DPI缩放` `#ImageGrab` `#WindowsAPI` `#客户区`
