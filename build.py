import os
import sys
import subprocess

def build_exe():
    print("开始打包PNG转JPG工具为可执行文件...")
    
    # 检查是否已安装PyInstaller
    try:
        import PyInstaller
        print("已检测到PyInstaller")
    except ImportError:
        print("未检测到PyInstaller，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("PyInstaller安装完成")
    
    # 构建命令
    cmd = [
        sys.executable, 
        "-m", 
        "PyInstaller",
        "--name=PNG转JPG自动转换工具",
        "--windowed",  # 不显示控制台窗口
        "--onefile",   # 打包成单个文件
        "--icon=NONE", # 默认图标
        "--clean",     # 清理临时文件
        "--hidden-import=PyQt5",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=watchdog",
        "--hidden-import=watchdog.observers",
        "--hidden-import=watchdog.events",
        "--collect-all=PyQt5",
        "--collect-all=PIL",
        "--collect-all=watchdog",
        "png2jpg.py"
    ]
    
    # 执行打包命令
    print("正在执行打包命令...")
    subprocess.check_call(cmd)
    
    print("\n打包完成！")
    print("可执行文件位于 dist 文件夹中")

if __name__ == "__main__":
    build_exe()