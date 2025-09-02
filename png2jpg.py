import sys
import os
import time
import shutil
import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QFileDialog, QSpinBox, QMessageBox,
                             QTextEdit, QScrollArea)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PIL import Image
import watchdog.observers
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class PngWatcher(FileSystemEventHandler):
    def __init__(self, source_folder, target_folder, log_signal=None):
        self.source_folder = source_folder
        self.target_folder = target_folder
        self.log_signal = log_signal
        
    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith('.png'):
            self.convert_png_to_jpg(event.src_path)
            
    def on_moved(self, event):
        if not event.is_directory and event.dest_path.lower().endswith('.png'):
            self.convert_png_to_jpg(event.dest_path)
    
    def convert_png_to_jpg(self, png_path):
        try:
            # 获取文件名（不含扩展名）
            filename = os.path.basename(png_path)
            name_without_ext = os.path.splitext(filename)[0]
            
            # 计算相对路径并保持子目录结构
            rel_path = os.path.relpath(png_path, self.source_folder)
            rel_dir = os.path.dirname(rel_path)
            target_dir = os.path.join(self.target_folder, rel_dir) if rel_dir else self.target_folder
            os.makedirs(target_dir, exist_ok=True)
            
            # 创建目标JPG文件路径
            jpg_path = os.path.join(target_dir, name_without_ext + '.jpg')
            
            # 使用PIL打开PNG并保存为JPG，保持高质量
            img = Image.open(png_path)
            img.save(jpg_path, 'JPEG', quality=100)
            
            # 获取当前时间
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_message = f"[{current_time}] 已转换: {png_path} -> {jpg_path}"
            
            # 转换完成后删除源PNG文件
            os.remove(png_path)
            log_message += " (已删除源文件)"
                
            # 发送日志信号
            if self.log_signal:
                self.log_signal.emit(log_message)
            else:
                print(log_message)
                
        except Exception as e:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 处理错误信息中的路径，确保只使用单个反斜杠
            error_str = str(e).replace("\\\\", "\\")
            error_message = f"[{current_time}] 转换失败: {png_path}, 错误: {error_str}"
            if self.log_signal:
                self.log_signal.emit(error_message)
            else:
                print(error_message)

class WatcherThread(QThread):
    conversion_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)
    
    def __init__(self, source_folder, target_folder, interval):
        super().__init__()
        self.source_folder = source_folder
        self.target_folder = target_folder
        self.interval = interval
        self.running = True
        
    def run(self):
        try:
            # 确保目标文件夹存在
            if not os.path.exists(self.target_folder):
                os.makedirs(self.target_folder)
                
            # 设置文件监视器（递归监控子目录）
            event_handler = PngWatcher(self.source_folder, self.target_folder, self.log_signal)
            observer = Observer()
            observer.schedule(event_handler, self.source_folder, recursive=True)
            observer.start()
            
            # 记录启动日志
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_signal.emit(f"[{current_time}] 开始监控文件夹: {self.source_folder}")
            
            # 检查现有的PNG文件（包含子目录）
            self.process_existing_files()
            
            # 保持线程运行，直到被停止
            while self.running:
                time.sleep(1)
                
            observer.stop()
            observer.join()
        except Exception as e:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 处理错误信息中的路径，确保只使用单个反斜杠
            error_str = str(e).replace("\\\\", "\\")
            self.error_signal.emit(f"[{current_time}] 监视器错误: {error_str}")
    
    def process_existing_files(self):
        try:
            for root, _, files in os.walk(self.source_folder):
                for filename in files:
                    if filename.lower().endswith('.png'):
                        png_path = os.path.join(root, filename)
                        name_without_ext = os.path.splitext(filename)[0]
                        
                        # 计算相对目录，保持子目录结构
                        rel_dir = os.path.relpath(root, self.source_folder)
                        target_dir = os.path.join(self.target_folder, rel_dir) if rel_dir != '.' else self.target_folder
                        os.makedirs(target_dir, exist_ok=True)
                        jpg_path = os.path.join(target_dir, name_without_ext + '.jpg')
                        
                        # 如果JPG不存在或PNG比JPG新，则转换
                        if not os.path.exists(jpg_path) or os.path.getmtime(png_path) > os.path.getmtime(jpg_path):
                            img = Image.open(png_path)
                            img.save(jpg_path, 'JPEG', quality=100)
                            
                            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            # 记录包含相对路径的日志
                            rel_png = os.path.relpath(png_path, self.source_folder)
                            rel_jpg = os.path.relpath(jpg_path, self.target_folder)
                            log_message = f"[{current_time}] 已转换: {rel_png} -> {rel_jpg}"
                            
                            # 转换完成后删除源PNG文件
                            os.remove(png_path)
                            log_message += " (已删除源文件)"
                                
                            self.log_signal.emit(log_message)
        except Exception as e:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 处理错误信息中的路径，确保只使用单个反斜杠
            error_str = str(e).replace("\\\\", "\\")
            self.error_signal.emit(f"[{current_time}] 处理现有文件错误: {error_str}")
    
    def stop(self):
        self.running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.watcher_thread = None
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('PNG转JPG自动转换工具')
        self.setGeometry(300, 300, 700, 500)
        
        # 主布局
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # 源文件夹选择
        source_layout = QHBoxLayout()
        source_label = QLabel('源文件夹:')
        self.source_edit = QLineEdit()
        source_button = QPushButton('浏览...')
        source_button.clicked.connect(self.select_source_folder)
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_edit)
        source_layout.addWidget(source_button)
        
        # 目标文件夹选择
        target_layout = QHBoxLayout()
        target_label = QLabel('目标文件夹:')
        self.target_edit = QLineEdit()
        target_button = QPushButton('浏览...')
        target_button.clicked.connect(self.select_target_folder)
        target_layout.addWidget(target_label)
        target_layout.addWidget(self.target_edit)
        target_layout.addWidget(target_button)
        
        # 检测间隔设置
        interval_layout = QHBoxLayout()
        interval_label = QLabel('检测间隔(秒):')
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 3600)
        self.interval_spin.setValue(5)
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_spin)
        
        # 添加提示标签
        delete_label = QLabel('转换完成后自动删除源文件')
        interval_layout.addWidget(delete_label)
        interval_layout.addStretch()
        
        # 控制按钮
        control_layout = QHBoxLayout()
        self.start_button = QPushButton('开始监控')
        self.start_button.clicked.connect(self.start_monitoring)
        self.stop_button = QPushButton('停止监控')
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        
        # 状态显示
        self.status_label = QLabel('就绪')
        self.status_label.setAlignment(Qt.AlignCenter)
        
        # 日志显示区域
        log_label = QLabel('转换日志:')
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        
        # 添加所有布局到主布局
        main_layout.addLayout(source_layout)
        main_layout.addLayout(target_layout)
        main_layout.addLayout(interval_layout)
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(log_label)
        main_layout.addWidget(self.log_text)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
    
    def select_source_folder(self):
        folder = QFileDialog.getExistingDirectory(self, '选择源文件夹')
        if folder:
            # 确保使用Windows风格的路径分隔符
            folder = folder.replace('/', '\\')
            self.source_edit.setText(folder)
    
    def select_target_folder(self):
        folder = QFileDialog.getExistingDirectory(self, '选择目标文件夹')
        if folder:
            # 确保使用Windows风格的路径分隔符
            folder = folder.replace('/', '\\')
            self.target_edit.setText(folder)
    
    def start_monitoring(self):
        source_folder = self.source_edit.text()
        target_folder = self.target_edit.text()
        interval = self.interval_spin.value()
        
        if not source_folder or not os.path.isdir(source_folder):
            QMessageBox.warning(self, '错误', '请选择有效的源文件夹')
            return
        
        if not target_folder or not os.path.isdir(target_folder):
            QMessageBox.warning(self, '错误', '请选择有效的目标文件夹')
            return
        
        # 禁用开始按钮，启用停止按钮
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText('正在监控...')
        
        # 清空日志
        self.log_text.clear()
        
        # 创建并启动监控线程
        self.watcher_thread = WatcherThread(source_folder, target_folder, interval)
        self.watcher_thread.conversion_signal.connect(self.update_status)
        self.watcher_thread.error_signal.connect(self.show_error)
        self.watcher_thread.log_signal.connect(self.update_log)
        self.watcher_thread.start()
    
    def stop_monitoring(self):
        if self.watcher_thread and self.watcher_thread.isRunning():
            self.watcher_thread.stop()
            self.watcher_thread.wait()  # 等待线程结束
            self.watcher_thread = None
        
        # 启用开始按钮，禁用停止按钮
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText('已停止监控')
    
    def update_status(self, message):
        self.status_label.setText(message)
    
    def show_error(self, error_message):
        QMessageBox.critical(self, '错误', error_message)
        self.update_log(error_message)
    
    def update_log(self, message):
        self.log_text.append(message)
        # 滚动到底部
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def closeEvent(self, event):
        # 关闭窗口时停止监控
        self.stop_monitoring()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
