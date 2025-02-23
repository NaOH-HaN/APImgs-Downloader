#author: NaOH_HaN
#date: 2025/2/23


import os
import sys
import time
import logging
import argparse
import requests
import threading
import webbrowser
from tqdm import tqdm
from queue import Queue
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional
from collections import deque
from colorama import Fore, Style, init

# 初始化colorama
init(autoreset=True)

class ConfigManager:
    """环境变量管理类"""
    def __init__(self):
        self._config = {
            'downloadPath': os.getcwd(),
            'multithreading': 4,
            'fetchPerRequest': 1,
            'requestUA': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'apiURL': 'https://www.loliapi.com/acg/'
        }
        self.lock = threading.Lock()

    def get(self, key: str) -> Any:
        with self.lock:
            return self._config.get(key)

    def set(self, key: str, value: Any) -> bool:
        with self.lock:
            if key in self._config:
                self._config[key] = value
                return True
            return False

class Statistics:
    """统计信息管理"""
    def __init__(self):
        self.total_downloaded = 0
        self.total_requests = 0
        self.total_success = 0
        self.total_size = 0
        self.history = deque(maxlen=100)
        self.lock = threading.Lock()

    def add_request(self):
        with self.lock:
            self.total_requests += 1

    def add_success(self, size: int):
        with self.lock:
            self.total_success += 1
            self.total_downloaded += 1
            self.total_size += size

class Downloader:
    """下载处理核心类"""
    def __init__(self, config: ConfigManager, stats: Statistics):
        self.config = config
        self.stats = stats
        self.executor = ThreadPoolExecutor(max_workers=config.get('multithreading'))
        self.speed_history = deque(maxlen=10)
        self.active = False

    def _get_image_url(self, img_id: Optional[int] = None) -> str:
        params = {}
        if img_id:
            params['id'] = img_id
        params['type'] = 'url'
        
        headers = {'User-Agent': self.config.get('requestUA')}
        api_url = self.config.get('apiURL')  # 获取正确的 API URL
        response = requests.get(
            api_url,
            params=params,
            headers=headers
        )
        response.raise_for_status()
        return response.text.strip()

    def _download_image(self, url: str, path: str):
        try:
            headers = {'User-Agent': self.config.get('requestUA')}
            response = requests.get(url, stream=True, headers=headers)
            response.raise_for_status()
            
            file_size = int(response.headers.get('content-length', 0))
            chunk_size = 1024
            downloaded = 0
            
            with open(path, 'wb') as f:
                start_time = time.time()
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        elapsed = time.time() - start_time
                        speed = downloaded / (elapsed + 1e-6)  # 防止除以0
                        self.speed_history.append(speed)
            
            self.stats.add_success(downloaded)
            return True
        except Exception as e:
            logging.error(f"Download failed: {str(e)}")
            return False

    def start_download(self, count: int):
        self.active = True
        futures = []
        for _ in range(count):
            futures.append(self.executor.submit(self._download_task))
        
        # 显示进度 显示进度时需要传递futures列表
        self._show_progress(futures)
        
        # 等待任务完成
        for future in futures:
            future.result()
            future.add_done_callback(self._task_complete)

    def _task_complete(self, future):
        try:
            future.result()
        except Exception as e:
            logging.error(f"任务失败: {str(e)}")
    
    def _download_task(self):
        try:
            url = self._get_image_url()
            filename = os.path.basename(url)
            save_path = os.path.join(self.config.get('downloadPath'), filename)
            return self._download_image(url, save_path)
        except Exception as e:
            logging.error(f"Task failed: {str(e)}", exc_info=True)  # 记录详细错误信息
            return False
    
    # 在Downloader类中添加进度显示逻辑
    def _show_progress(self, futures):
        if not futures:
            print(Fore.YELLOW + "没有需要下载的任务")
            return

        completed = 0
        start_time = time.time()
        last_size = 0
        current_size = 0

        with tqdm(
            total=len(futures),
            desc=f"{Fore.GREEN}Downloading{Style.RESET_ALL}",
            bar_format=f"{Fore.GREEN}{{l_bar}}{{bar}}{Style.RESET_ALL} {{r_bar}}",
            ncols=80
        ) as pbar:
            while completed < len(futures):
                # 计算完成数量
                new_completed = sum(f.done() for f in futures)
                delta = new_completed - completed
                completed = new_completed

                # 计算速度统计
                current_size = self.stats.total_size
                elapsed = time.time() - start_time
                delta_size = current_size - last_size
                speeds = [s for s in self.speed_history if s > 0]
                
                # 更新进度条
                pbar.update(delta)
                pbar.set_postfix({
                    'speed': f"{delta_size/elapsed/1024:.1f}KB/s" if elapsed > 0 else "0KB/s",
                    'success': f"{self.stats.total_success}/{self.stats.total_requests}",
                    'size': f"{current_size/1024/1024:.2f}MB"
                })

                last_size = current_size
                start_time = time.time()
                time.sleep(0.5)

class CommandHandler:
    """命令解析和处理类"""
    def __init__(self, downloader: Downloader, config: ConfigManager, stats: Statistics):
        self.downloader = downloader
        self.config = config
        self.stats = stats
        self.commands = {
            '/help': self.show_help,
            '/env': self.handle_env,
            '/logcat': self.handle_logcat,
            '/stats': self.show_stats,
            '/about': self.show_about,
            '/download': self.handle_download,
            '/apiweb': self.open_api_web,
            '/exit': self.handle_exit
        }

    def handle_download(self, args):
        if not args:
            print(Fore.RED + "用法: /download [数量] ")
            return
        
        try:
            count = int(args[0])
            if count < 1:
                raise ValueError
        except ValueError:
            print(Fore.RED + "请输入有效的正整数")
            return
        
        per_request = self.config.get('fetchPerRequest')
        total_requests = (count + per_request - 1) // per_request
        
        print(Fore.CYAN + f"开始下载 {count} 张图片（每次请求获取 {per_request} 张）...")
        
        # 发起下载请求
        for _ in range(total_requests):
            actual_count = min(per_request, count)
            self.downloader.start_download(actual_count)
            count -= actual_count
            if count <= 0:
                break
        self.show_stats(None)

    
    def process_command(self, cmd: str):
        parts = cmd.split()
        if not parts:
            return
        
        handler = self.commands.get(parts[0])
        if handler:
            handler(parts[1:])
        else:
            print(Fore.RED + "未知命令。输入 /help 查看可用命令。")
    
    def show_help(self, _):
        help_text = f"""
    {Fore.CYAN}可用命令:{Style.RESET_ALL}
    {Fore.YELLOW}/help{Style.RESET_ALL} - 显示本帮助信息
    {Fore.YELLOW}/env [key] [query/set] [value]{Style.RESET_ALL} - 管理配置参数
        支持的key: downloadPath, multithreading, fetchPerRequest, requestUA
        示例: /env multithreading set 8
    
    {Fore.YELLOW}/logcat start/stop/path{Style.RESET_ALL} - 日志管理
        /logcat start - 开始记录日志
        /logcat stop - 停止记录日志
        /logcat path set /path/to/logs - 设置日志存储路径
    
    {Fore.YELLOW}/stats{Style.RESET_ALL} - 显示下载统计信息
    {Fore.YELLOW}/about{Style.RESET_ALL} - 显示程序信息

    {Fore.CYAN}可用命令:{Style.RESET_ALL}
    {Fore.YELLOW}/help{Style.RESET_ALL} - 显示本帮助信息
    {Fore.YELLOW}/download [数量]{Style.RESET_ALL} - 启动下载任务
    {Fore.YELLOW}/env [key] [query/set] [value]{Style.RESET_ALL} - 管理配置参数
    {Fore.YELLOW}/apiweb {Style.RESET_ALL} - 打开API网页
    """
        print(help_text)

    def show_stats(self, _):
        with self.stats.lock:
            stats_data = {
                'total_requests': self.stats.total_requests,
                'total_downloaded': self.stats.total_downloaded,
                'success_rate': (self.stats.total_success / self.stats.total_requests * 100) 
                            if self.stats.total_requests > 0 else 0,
                'total_size': self.stats.total_size,
                'avg_speed': (sum(self.downloader.speed_history)/len(self.downloader.speed_history)) 
                            if self.downloader.speed_history else 0
            }

        print(f"{Fore.CYAN}=== 统计信息 ==={Style.RESET_ALL}")
        print(f"{Fore.YELLOW}请求总数:{Style.RESET_ALL} {stats_data['total_requests']}")
        print(f"{Fore.YELLOW}下载总数:{Style.RESET_ALL} {stats_data['total_downloaded']}")
        print(f"{Fore.YELLOW}成功率:{Style.RESET_ALL} {stats_data['success_rate']:.2f}%")
        print(f"{Fore.YELLOW}下载总大小:{Style.RESET_ALL} {stats_data['total_size']/1024/1024:.2f} MB")
        print(f"{Fore.YELLOW}平均速度:{Style.RESET_ALL} {stats_data['avg_speed']/1024:.2f} KB/s")
    
    # 在CommandHandler类中完善命令处理
    def handle_env(self, args):
        if len(args) < 1:
            print(Fore.RED + "用法: /env [key] [query/set] [value]")
            return

        key = args[0]
        valid_keys = ['downloadPath', 'multithreading', 'fetchPerRequest', 'requestUA', "apiURL"]

        # 查询操作
        if len(args) == 1 or (len(args) >= 2 and args[1] == 'query'):
            if key not in valid_keys:
                print(Fore.RED + f"无效的配置key。有效key: {', '.join(valid_keys)}")
                return
            value = self.config.get(key)
            print(Fore.CYAN + f"{key}: {value}")
            return

        # 设置操作
        if args[1] == 'set':
            if key not in valid_keys:
                print(Fore.RED + f"无效的配置key。有效key: {', '.join(valid_keys)}")
                return

            value = ' '.join(args[2:])  # 处理带空格的参数
            
            # 参数验证
            if key == 'downloadPath':
                if not os.path.exists(value):
                    print(Fore.RED + "路径不存在！")
                    return
                value = os.path.abspath(value)

            elif key == 'multithreading':
                try:
                    value = int(value)
                    if not 1 <= value <= 16:
                        raise ValueError
                except ValueError:
                    print(Fore.RED + "必须是1-16之间的整数")
                    return

            elif key == 'fetchPerRequest':
                try:
                    value = int(value)
                    if not 1 <= value <= 100:
                        raise ValueError
                except ValueError:
                    print(Fore.RED + "必须是1-100之间的整数")
                    return

            # 更新配置
            if self.config.set(key, value):
                print(Fore.GREEN + f"已更新 {key} => {value}")
                # 动态调整线程池
                if key == 'multithreading':
                    self.downloader.executor.shutdown(wait=True)
                    self.downloader.executor = ThreadPoolExecutor(
                        max_workers=self.config.get('multithreading')
                    )
            else:
                print(Fore.RED + "配置更新失败")
    
    def handle_logcat(self, args):
        if not args:
            print(Fore.RED + "用法: /logcat [start/stop/path/level]")
            return

        action = args[0].lower()
        
        # 处理路径设置
        if action == "path":
            if len(args) < 2:
                print(Fore.RED + "用法: /logcat path [query/set] [value]")
                return
                
            sub_action = args[1].lower()
            if sub_action == "query":
                print(Fore.CYAN + f"当前日志路径：{log_manager.log_path}")
            elif sub_action == "set":
                if len(args) < 3:
                    print(Fore.RED + "需要指定路径")
                    return
                path = ' '.join(args[2:])
                if log_manager.set_log_path(path):
                    print(Fore.GREEN + f"日志路径已更新：{path}")
                else:
                    print(Fore.RED + "路径设置失败")
            else:
                print(Fore.RED + "无效操作")
        
        # 处理启停命令
        elif action == "start":
            log_manager.start_logging()
            print(Fore.GREEN + "日志记录已启动")
        elif action == "stop":
            log_manager.stop_logging()
            print(Fore.YELLOW + "日志记录已停止")
        elif action == "level":
            if len(args) < 2:
                print(Fore.RED + "用法: /logcat level [info/warning/error/...]")
                return
            level = args[1].lower()
            if log_manager.set_log_level(level):
                print(Fore.GREEN + f"日志级别已设置为：{level.upper()}")
            else:
                print(Fore.RED + "无效的日志级别")
        else:
            print(Fore.RED + "无效命令")

    def show_about(self, _):
        # 显示程序信息
        print(Fore.CYAN + "ACG 图片下载器 v1.0")
        print(Fore.CYAN + "Developed by NaOH-HaN with love，Licence under GPLv3 Licence.")
    

    def open_api_web(self, _): # import webbrowser
        api_url = self.config.get('apiURL')
        print(Fore.CYAN + f"正在打开API网页: {api_url}")
        webbrowser.open(api_url)

    def handle_exit(self, _):
        print(Fore.YELLOW + "正在退出...")
        self.downloader.executor.shutdown()
        sys.exit(0)

class LogManager:
    def __init__(self):
        self.logger = logging.getLogger('ACGDownloader')
        self.logger.setLevel(logging.DEBUG)
        self.file_handler = None
        self.enabled = False
        self.log_path = os.getcwd()
        
        # 保留控制台输出
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        self.logger.addHandler(console_handler)

    def start_logging(self):
        if self.enabled:
            self.logger.warning("日志记录已在进行中")
            return

        try:
            # 确保日志目录存在
            os.makedirs(self.log_path, exist_ok=True)
            
            # 创建带时间戳的日志文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.log_path, f"acg_download_{timestamp}.log")
            
            # 配置文件处理器
            self.file_handler = logging.FileHandler(filename, encoding='utf-8')
            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            self.file_handler.setFormatter(formatter)
            self.logger.addHandler(self.file_handler)
            
            self.enabled = True
            self.logger.info("=== 日志记录已启动 ===")
            self.logger.info(f"日志文件位置：{filename}")
        except Exception as e:
            self.logger.error(f"启动日志失败：{str(e)}", exc_info=True)  # 记录详细错误信息

    def stop_logging(self):
        if not self.enabled:
            self.logger.warning("日志记录未启用")
            return
            
        try:
            self.logger.info("=== 日志记录已停止 ===")
            if self.file_handler:
                self.file_handler.close()
                self.logger.removeHandler(self.file_handler)
            self.enabled = False
        except Exception as e:
            self.logger.error(f"停止日志失败：{str(e)}")

    def set_log_path(self, path):
        if not os.path.isdir(path):
            try:
                os.makedirs(path, exist_ok=True)
            except:
                return False
        self.log_path = os.path.abspath(path)
        return True

    def set_log_level(self, level):
        level = level.upper()
        if level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            self.logger.setLevel(getattr(logging, level))
            for handler in self.logger.handlers:
                handler.setLevel(getattr(logging, level))
            return True
        return False

class LoggerWriter:
    def __init__(self, log_func):
        self.log_func = log_func
        
    def write(self, message):
        if message.strip():
            self.log_func(message.strip())
            
    def flush(self):
        pass

def main():
    # 初始化各组件
    config = ConfigManager()
    stats = Statistics()
    downloader = Downloader(config, stats)
    global log_manager
    log_manager = LogManager()
    log_manager.set_log_level('DEBUG')  # 设置日志级别为 DEBUG
    log_manager.start_logging()  # 默认启用日志记录
    handler = CommandHandler(downloader, config, stats)
    
    # 启动时显示信息
    print(Fore.GREEN + "=== API 图片下载器 ===")
    print(Fore.YELLOW + f"下载路径: {config.get('downloadPath')}")
    print(Fore.YELLOW + f"线程: {config.get('multithreading')}")
    print(Fore.BLUE + "\n默认API提供商：https://www.loliapi.cn/")
    print(Fore.RED + "[重要提示] 请合理使用默认API，避免高频请求造成服务压力！")
    print(Fore.GREEN + "=== API 图片下载器 ===")

    # 主循环
    while True:
        try:
            cmd = input(Fore.BLUE + ">>> " + Style.RESET_ALL)
            if cmd.startswith('/'):
                handler.process_command(cmd)
            else:
                print(Fore.RED + "Invalid command. Type /help for available commands.")
        except KeyboardInterrupt:
            print(Fore.YELLOW + "\nCtrl+C 已按下，程序将立即停止...")
            downloader.executor.shutdown()
            sys.exit(0)

if __name__ == "__main__":
    main()