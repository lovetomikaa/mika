#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
米卡桌面控制脚本 v2 - Mika Desktop Control
==========================================
支持：
1. 单步操作（每个命令快速完成）
2. 停止信号检查（操作前检查 stop_signal 文件）
3. 分步执行（大操作拆成小步骤）

用法：
  python mika_desktop_control.py <action> [args...]
  
操作列表：
  move <x> <y>              移动鼠标到坐标
  click [left|right|middle] 点击（默认左键）
  double_click              双击
  right_click               右键
  scroll <n> [up|down]      滚动
  drag <x1> <y1> <x2> <y2>  拖拽
  position                  获取鼠标位置
  screenshot [path]         截图
  type <text>               打字
  press <key>               按键
  hotkey <k1> <k2> ...      组合键
  screen_size               屏幕尺寸
  stop                      发出停止信号
  clear_stop                清除停止信号
  check_stop                检查是否有停止信号
"""

import ctypes
import pyautogui
import sys
import os
import json
import time
from datetime import datetime

# ============== DPI 校准 ==============
# 你的屏幕 2560x1440，Windows 缩放 125%
# 必须设置 DPI 感知，让 PyAutoGUI 用物理像素坐标
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
    except:
        pass

# ============== 配置 ==============
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, "mika_control.log")
STOP_SIGNAL = os.path.join(SCRIPT_DIR, "stop_signal")

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1


def log(msg):
    """记录日志"""
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except:
        pass


def check_stop():
    """检查停止信号，如果有则退出"""
    if os.path.exists(STOP_SIGNAL):
        # 清除信号
        try:
            os.remove(STOP_SIGNAL)
        except:
            pass
        log("!! STOP SIGNAL DETECTED !!")
        print("STOPPED")
        sys.exit(0)


def output(result):
    """输出结果（JSON格式）"""
    print(json.dumps(result, ensure_ascii=False))


# ============== 操作函数 ==============

def do_move(x, y, duration=0.5):
    check_stop()
    log(f"MOVE -> ({x}, {y})")
    pyautogui.moveTo(int(x), int(y), duration=float(duration))
    output({"ok": True, "action": "move", "x": int(x), "y": int(y)})

def do_click(button='left'):
    check_stop()
    log(f"CLICK {button}")
    pyautogui.click(button=button)
    output({"ok": True, "action": "click", "button": button})

def do_double_click():
    check_stop()
    log("DOUBLE_CLICK")
    pyautogui.doubleClick()
    output({"ok": True, "action": "double_click"})

def do_right_click():
    check_stop()
    log("RIGHT_CLICK")
    pyautogui.rightClick()
    output({"ok": True, "action": "right_click"})

def do_scroll(n, direction='down'):
    check_stop()
    amount = int(n) if direction == 'down' else -int(n)
    log(f"SCROLL {n} {direction}")
    pyautogui.scroll(amount)
    output({"ok": True, "action": "scroll", "amount": amount})

def do_drag(x1, y1, x2, y2, duration=0.5):
    check_stop()
    log(f"DRAG ({x1},{y1}) -> ({x2},{y2})")
    pyautogui.moveTo(int(x1), int(y1))
    pyautogui.drag(int(x2)-int(x1), int(y2)-int(y1), duration=float(duration))
    output({"ok": True, "action": "drag"})

def do_position():
    pos = pyautogui.position()
    output({"ok": True, "x": pos.x, "y": pos.y})

def do_screenshot(path=None):
    check_stop()
    if not path:
        path = os.path.join(SCRIPT_DIR, "screenshot.png")
    log(f"SCREENSHOT -> {path}")
    s = pyautogui.screenshot()
    s.save(path)
    output({"ok": True, "action": "screenshot", "path": path})

def do_type(text):
    check_stop()
    log(f"TYPE: {text}")
    pyautogui.typewrite(text, interval=0.05)
    output({"ok": True, "action": "type"})

def do_press(key):
    check_stop()
    log(f"PRESS: {key}")
    pyautogui.press(key)
    output({"ok": True, "action": "press", "key": key})

def do_hotkey(*keys):
    check_stop()
    log(f"HOTKEY: {'+'.join(keys)}")
    pyautogui.hotkey(*keys)
    output({"ok": True, "action": "hotkey", "keys": list(keys)})

def do_screen_size():
    s = pyautogui.size()
    output({"ok": True, "width": s.width, "height": s.height})

def do_stop():
    """发出停止信号"""
    with open(STOP_SIGNAL, 'w') as f:
        f.write(str(time.time()))
    log("Stop signal SENT")
    output({"ok": True, "action": "stop", "message": "Stop signal sent"})

def do_clear_stop():
    """清除停止信号"""
    if os.path.exists(STOP_SIGNAL):
        os.remove(STOP_SIGNAL)
    output({"ok": True, "action": "clear_stop"})

def do_check_stop():
    """检查停止信号"""
    has_stop = os.path.exists(STOP_SIGNAL)
    if has_stop:
        try:
            os.remove(STOP_SIGNAL)
        except:
            pass
    output({"ok": True, "stop": has_stop})


# ============== 主程序 ==============

def main():
    if len(sys.argv) < 2:
        print("Usage: python mika_desktop_control.py <action> [args...]")
        sys.exit(1)
    
    action = sys.argv[1]
    args = sys.argv[2:]
    
    try:
        if action == 'move':
            do_move(args[0], args[1], args[2] if len(args) > 2 else 0.5)
        elif action == 'click':
            do_click(args[0] if args else 'left')
        elif action == 'double_click':
            do_double_click()
        elif action == 'right_click':
            do_right_click()
        elif action == 'scroll':
            do_scroll(args[0] if args else 3, args[1] if len(args) > 1 else 'down')
        elif action == 'drag':
            do_drag(args[0], args[1], args[2], args[3])
        elif action == 'position':
            do_position()
        elif action == 'screenshot':
            do_screenshot(args[0] if args else None)
        elif action == 'type':
            do_type(' '.join(args))
        elif action == 'press':
            do_press(args[0])
        elif action == 'hotkey':
            do_hotkey(*args)
        elif action == 'screen_size':
            do_screen_size()
        elif action == 'stop':
            do_stop()
        elif action == 'clear_stop':
            do_clear_stop()
        elif action == 'check_stop':
            do_check_stop()
        else:
            output({"ok": False, "error": f"Unknown action: {action}"})
            sys.exit(1)
            
    except pyautogui.FailSafeException:
        output({"ok": False, "error": "FAILSAFE triggered (mouse at corner)"})
        sys.exit(1)
    except IndexError:
        output({"ok": False, "error": f"Missing arguments for: {action}"})
        sys.exit(1)
    except SystemExit:
        raise
    except Exception as e:
        output({"ok": False, "error": str(e)})
        sys.exit(1)


if __name__ == '__main__':
    main()
