###############################################################################
# Trình Giám Sát Tiến Trình & Quản Lý Tài Nguyên Nâng Cao
# Giao diện tiện ích hệ thống chuyên nghiệp
###############################################################################

import tkinter as tk
from tkinter import ttk, messagebox
import requests
import urllib3
import json
from base64 import b64encode
from time import sleep
import os
import threading
import psutil
import win32gui
import win32process
import random
from datetime import datetime

class SystemProcessManager:
    def __init__(self, root):
        self.root = root
        self.setup_window()
        self.setup_variables()
        self.setup_styles()
        self.create_widgets()
        
        # Biến kết nối tiến trình
        self.is_monitoring = False
        self.session = None
        self.headers = None
        self.protocol = None
        self.host = '127.0.0.1'
        self.port = None
        self.process_id = None
        self.worker_thread = None
        
        # Dữ liệu phân bổ tài nguyên - ID tiến trình ánh xạ tên tướng chuẩn theo Riot API
        self.system_resources = {
            "99": "Lux",             # từ ví dụ trước là TàiNguyênA
            "800": "Mel",
            "54": "Malphite",
            "84": "Akali",
            "53": "Blitzcrank",
            "245": "Ekko",
            "3": "Galio",
            "555": "Pyke",
            "254": "Vi",
            "234": "Viego",
            "134": "Syndra",
            "517": "Sylas",
            "59": "JarvanIV",
            "12": "Alistar",
            "64": "LeeSin",
            "7": "Leblanc",
            "110": "Varus",
            "121": "Khazix",
            "105": "Fizz",
            "126": "Jayce"
        }
        self.resource_ids = {
            "Lux": 99,
            "Mel": 800,
            "Malphite": 54,
            "Akali": 84,
            "Blitzcrank": 53,
            "Ekko": 245,
            "Galio": 3,
            "Pyke": 555,
            "Vi": 254,
            "Viego": 234,
            "Syndra": 134,
            "Sylas": 517,
            "JarvanIV": 59,
            "Alistar": 12,
            "LeeSin": 64,
            "Leblanc": 7,
            "Varus": 110,
            "Khazix": 121,
            "Fizz": 105,
            "Jayce": 126
        }
        self.allocated_resources = []
        
        # Nếu cần ID thay thế (ví dụ: skin khác, phiên bản khác)
        self.alternative_resource_ids = {
            "Mel": [800, 950, 980, 910]  # Nhiều ID phân bổ tài nguyên
        }
        
        # Trạng thái lựa chọn tiến trình
        self.last_allocation = None
        self.selected_resources = []  
        self.selected_resource_names = []  
        
        # Trạng thái kết nối
        self.is_connected = False
        
        # Theo dõi trạng thái tiến trình
        self.current_process_session = None
        self.has_allocated_in_session = False
        
        # Bắt đầu giám sát hệ thống nền
        self.start_background_monitor()
        
    def start_background_monitor(self):
        """Bắt đầu giám sát nền cho tiến trình đích"""
        self.log_system_message("KHỞI_TẠO_HT: Đang chờ khởi tạo tiến trình đích")
        # Bắt đầu luồng giám sát
        monitoring_thread = threading.Thread(target=self.background_monitor, daemon=True)
        monitoring_thread.start()
        
    def background_monitor(self):
        """Giám sát nền cho trạng thái kết nối tiến trình"""
        while True:
            try:
                # Kiểm tra xem tiến trình đích có đang chạy không
                process_running = self.detect_target_process() is not None
                
                if process_running and not self.is_connected:
                    # Tiến trình vừa khởi động
                    self.is_connected = True
                    self.log_system_message("KẾT_NỐI_TC: Đã phát hiện tiến trình và thiết lập kết nối")
                    
                    # Thử thiết lập kết nối
                    process_dir = self.detect_target_process()
                    if process_dir:
                        lockpath = os.path.join(process_dir, 'lockfile')
                        if os.path.isfile(lockpath):
                            try:
                                with open(lockpath, 'r') as f:
                                    lockdata = f.read()
                                
                                lock = lockdata.split(':')
                                self.protocol = lock[4]
                                self.port = lock[2]
                                username = 'riot'
                                password = lock[3]
                                
                                # Thiết lập phiên
                                userpass = b64encode(f'{username}:{password}'.encode()).decode('ascii')
                                self.headers = {'Authorization': f'Basic {userpass}'}
                                self.session = requests.session()
                                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                                
                                # Tự động kiểm tra phân bổ tài nguyên khi kết nối
                                if self.selected_resource_names:
                                    if len(self.selected_resource_names) == 1:
                                        # Tài nguyên đơn - kiểm tra sau khi tiến trình tải
                                        resource_name = self.selected_resource_names[0]
                                        self.root.after(4000, lambda: self.check_single_resource_allocation(resource_name))
                                    else:
                                        # Nhiều tài nguyên - kiểm tra với tải
                                        self.root.after(4000, lambda: self.check_multiple_resources_allocation(self.selected_resource_names))
                                
                            except Exception as e:
                                self.log_system_message(f"LỖI_KN: Kết nối thất bại - {str(e)}")
                                
                elif not process_running and self.is_connected:
                    # Tiến trình đã bị kết thúc
                    self.is_connected = False
                    self.log_system_message("KHỞI_TẠO_HT: Đang chờ khởi tạo tiến trình đích")
                    
            except Exception as e:
                pass  # Im lặng xử lý lỗi trong giám sát nền
                
            sleep(3)  # Kiểm tra mỗi 3 giây
            
    def on_resource_selected(self, event=None):
        """Xử lý lựa chọn tài nguyên từ giao diện"""
        if not self.is_connected:
            self.log_system_message(f"CẢNH_BÁO_TT: Tiến trình đích phải được khởi tạo trước khi phân bổ tài nguyên")
            return
            
    def check_resource_allocation(self, resource_name):
        """Kiểm tra xem tài nguyên đã chọn có được phân bổ không - Kiểm tra tương thích hệ thống"""
        try:
            if not self.session or not self.headers:
                self.log_system_message(f"CẢNH_BÁO_PHIÊN: Phiên chưa được thiết lập để xác thực tài nguyên")
                return
                
            # Thử các điểm cuối API khác nhau để xác thực dữ liệu tài nguyên
            endpoints = [
                '/lol-champions/v1/owned-champions-minimal',
                '/lol-champions/v1/inventories/1/champions-minimal',
                '/lol-champions/v1/inventories/1/champions',
                '/lol-champions/v1/inventories/CHAMPION/champions',
                '/lol-collections/v1/inventories/CHAMPION'
            ]
            
            allocated_resources = []
            
            for endpoint in endpoints:
                try:
                    r = self.request('get', endpoint)
                    if r.status_code == 200:
                        allocated = r.json()
                        if isinstance(allocated, list):
                            for resource in allocated:
                                if isinstance(resource, dict):
                                    resource_id = resource.get('id') or resource.get('championId') or resource.get('itemId')
                                    if resource_id and resource.get('active', True):
                                        allocated_resources.append(resource_id)
                        elif isinstance(allocated, dict) and 'champions' in allocated:
                            for resource in allocated['champions']:
                                resource_id = resource.get('id') or resource.get('championId') or resource.get('itemId')
                                if resource_id and resource.get('active', True):
                                    allocated_resources.append(resource_id)
                        
                        if allocated_resources:
                            break
                except Exception:
                    continue
            
            if not allocated_resources:
                self.log_system_message(f"CẢNH_BÁO_PHÂN_BỔ: Xác thực tài nguyên không khả dụng - tiến hành phân bổ trực tiếp")
                return
                
            # Kiểm tra phân bổ nâng cao với ID thay thế
            primary_id = self.resource_ids.get(resource_name)
            alt_ids = self.alternative_resource_ids.get(resource_name, [])
            all_ids_to_check = [primary_id] + alt_ids if primary_id else alt_ids
            
            resource_found = False
            found_id = None
            
            for resource_id in all_ids_to_check:
                if resource_id and resource_id in allocated_resources:
                    resource_found = True
                    found_id = resource_id
                    # Cập nhật ID chính nếu tìm thấy thay thế
                    if resource_id != primary_id:
                        self.resource_ids[resource_name] = resource_id
                    break
            
            if resource_found:
                self.log_system_message(f"TÀI_NGUYÊN_HỢP_LỆ: Đã xác nhận phân bổ {resource_name}")
            else:
                self.log_system_message(f"TÀI_NGUYÊN_KHÔNG_CÓ: {resource_name} không có sẵn trong kho phân bổ hiện tại")
                self.log_system_message(f"THÔNG_TIN_KHO: Tổng tài nguyên đã phân bổ: {len(allocated_resources)}")
                
        except Exception as e:
            self.log_system_message(f"LỖI_XÁC_THỰC: Xác thực tài nguyên {resource_name} thất bại - {str(e)}")
        
    def setup_window(self):
        self.root.title("Quản Lý Tài Nguyên Hệ Thống")
        self.root.geometry("600x750")
        self.root.resizable(True, True)  # Cho phép thay đổi kích thước
        
        # Đặt kích thước tối thiểu
        self.root.minsize(350, 400)
        
        # Xóa biểu tượng cửa sổ - thử nhiều phương pháp
        try:
            self.root.iconbitmap('')
        except:
            try:
                self.root.wm_iconbitmap('')
            except:
                try:
                    self.root.iconphoto(True, tk.PhotoImage())
                except:
                    pass
        
        # Nền chủ đề tối hiện đại
        self.root.configure(bg='#1e1e1e')
        self.center_window()
        
        # Ràng buộc sự kiện thay đổi kích thước cho thiết kế đáp ứng
        self.root.bind('<Configure>', self.on_window_resize)
        
    def on_window_resize(self, event):
        """Xử lý sự kiện thay đổi kích thước cửa sổ cho thiết kế đáp ứng"""
        if event.widget == self.root:
            # Điều chỉnh kích thước phông chữ dựa trên kích thước cửa sổ
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            
            # Tính hệ số tỷ lệ
            base_width, base_height = 600, 750
            scale_x = width / base_width
            scale_y = height / base_height
            scale = min(scale_x, scale_y)
            
            # Tỷ lệ tối thiểu để giữ văn bản có thể đọc được
            scale = max(scale, 0.6)
            
            # Cập nhật phong cách dựa trên tỷ lệ
            self.update_responsive_styles(scale)
    
    def update_responsive_styles(self, scale):
        """Cập nhật phong cách dựa trên tỷ lệ cho thiết kế đáp ứng"""
        try:
            style = ttk.Style()
            
            # Tính kích thước phông chữ
            title_size = max(int(20 * scale), 12)
            subtitle_size = max(int(14 * scale), 10)
            button_size = max(int(12 * scale), 9)
            text_size = max(int(11 * scale), 8)
            
            # Cập nhật phong cách
            style.configure('Title.TLabel', font=('Segoe UI', title_size, 'bold'))
            style.configure('Subtitle.TLabel', font=('Segoe UI', subtitle_size))
            style.configure('Custom.TCheckbutton', font=('Segoe UI', text_size))
            
            # Cập nhật phông chữ nút
            if hasattr(self, 'select_resource_button'):
                self.select_resource_button.config(font=('Segoe UI', button_size, 'bold'))
            if hasattr(self, 'start_button'):
                self.start_button.config(font=('Segoe UI', button_size, 'bold'))
            
        except Exception:
            pass  # Im lặng xử lý lỗi cập nhật phông chữ
        
    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def setup_variables(self):
        self.selected_resource = tk.StringVar(value="Lux")
        self.auto_execute = tk.BooleanVar(value=True)
        self.execution_delay = tk.StringVar(value="0")
        
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Cấu hình phong cách VIP hiện đại với gradient và vẻ ngoài chuyên nghiệp
        style.configure('Title.TLabel', 
                       background='#1e1e1e', 
                       foreground='#00d4aa',
                       font=('Segoe UI', 20, 'bold'))
        
        style.configure('Subtitle.TLabel',
                       background='#1e1e1e',
                       foreground='#ffffff',
                       font=('Segoe UI', 12))
        
        style.configure('Custom.TCheckbutton',
                       background='#1e1e1e',
                       foreground='#ffffff',
                       font=('Segoe UI', 11),
                       focuscolor='none')
        
        style.configure('VIP.TButton',
                       font=('Segoe UI', 14, 'bold'),
                       padding=(20, 10))
        
    def create_widgets(self):
        # Khung chính với lưới đáp ứng
        main_frame = tk.Frame(self.root, bg='#1e1e1e')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Cấu hình trọng số lưới cho đáp ứng
        main_frame.grid_rowconfigure(5, weight=1)  # Vùng log sẽ mở rộng
        
        # Tiêu đề VIP với hiệu ứng gradient
        title_frame = tk.Frame(main_frame, bg='#1e1e1e')
        title_frame.pack(fill='x', pady=(0, 20))
        
        title_label = ttk.Label(title_frame, text="⚡ QUẢN LÝ TÀI NGUYÊN HỆ THỐNG", style='Title.TLabel')
        title_label.pack()
        
        version_label = ttk.Label(title_frame, text="Phiên Bản Chuyên Nghiệp", 
                                style='Subtitle.TLabel')
        version_label.pack()
        
        # Phần phân bổ tài nguyên với kiểu dáng VIP
        resource_frame = tk.LabelFrame(main_frame, text="Điều Khiển Phân Bổ Tài Nguyên", 
                                     bg='#2d2d2d', fg='#00d4aa', 
                                     font=('Segoe UI', 12, 'bold'), padx=20, pady=15,
                                     relief='groove', bd=2)
        resource_frame.pack(fill='x', pady=(0, 15))
        
        # Nút lựa chọn tài nguyên với kiểu dáng VIP
        self.select_resource_button = tk.Button(resource_frame, text="🎯 CẤU HÌNH TÀI NGUYÊN",
                                               command=self.open_resource_selection_dialog,
                                               font=('Segoe UI', 12, 'bold'),
                                               bg='#0066cc', fg='white',
                                               activebackground='#0052a3',
                                               relief='raised', bd=3,
                                               padx=25, pady=12,
                                               cursor='hand2')
        self.select_resource_button.pack(pady=(0, 10))
        
        # Hiển thị tài nguyên với kiểu dáng hiện đại
        self.resources_display_frame = tk.Frame(resource_frame, bg='#2d2d2d')
        self.resources_display_frame.pack(anchor='w', pady=(5, 0), fill='x')
        
        self.resources_label = tk.Label(self.resources_display_frame, 
                                       text="Chưa cấu hình tài nguyên", bg='#2d2d2d', fg='#cccccc', 
                                       font=('Segoe UI', 10), wraplength=450)
        self.resources_label.pack(side='left', anchor='w')
        
        # Chỉ báo tải với hoạt hình hiện đại
        self.loading_frame = tk.Frame(resource_frame, bg='#2d2d2d')
        self.loading_label = tk.Label(self.loading_frame, 
                                    text="⏳ Đang xác thực phân bổ tài nguyên...", 
                                    bg='#2d2d2d', fg='#ff9500', 
                                    font=('Segoe UI', 9))
        self.loading_label.pack()
        
        # Điều khiển thời gian thực thi
        timing_label = tk.Label(resource_frame, text="Độ Trễ Thực Thi (ms):", 
                             bg='#2d2d2d', fg='#cccccc', font=('Segoe UI', 10))
        timing_label.pack(anchor='w', pady=(8, 3))
        
        timing_entry = tk.Entry(resource_frame, textvariable=self.execution_delay, 
                             width=12, font=('Segoe UI', 10), bg='#404040', fg='white',
                             insertbackground='white', relief='flat', bd=5)
        timing_entry.pack(anchor='w')
        
        # Cài đặt thực thi tự động
        execution_frame = tk.LabelFrame(main_frame, text="Cài Đặt Thực Thi", 
                                 bg='#2d2d2d', fg='#00d4aa', 
                                 font=('Segoe UI', 12, 'bold'), padx=20, pady=15,
                                 relief='groove', bd=2)
        execution_frame.pack(fill='x', pady=(0, 15))
        
        ttk.Checkbutton(execution_frame, text="Tự động khóa tài nguyên sau phân bổ", 
                       variable=self.auto_execute, style='Custom.TCheckbutton').pack(anchor='w')
        
        # Bảng điều khiển với các nút VIP
        control_frame = tk.Frame(main_frame, bg='#1e1e1e')
        control_frame.pack(fill='x', pady=(0, 15))
        
        self.start_button = tk.Button(control_frame, text="⚡ KHỞI TẠO HỆ THỐNG", 
                                    command=self.toggle_system_monitor,
                                    font=('Segoe UI', 14, 'bold'),
                                    bg='#00cc44', fg='white',
                                    activebackground='#00b33c',
                                    activeforeground='white',
                                    relief='raised',
                                    bd=4, padx=40, pady=12,
                                    cursor='hand2')
        self.start_button.pack()
        
        # Phần trạng thái hệ thống với thiết kế hiện đại
        status_frame = tk.LabelFrame(main_frame, text="Giám Sát Hệ Thống", 
                                   bg='#2d2d2d', fg='#00d4aa', 
                                   font=('Segoe UI', 12, 'bold'), padx=10, pady=10,
                                   relief='groove', bd=2)
        status_frame.pack(fill='both', expand=True)
        
        # Vùng log với giao diện terminal hiện đại
        log_frame = tk.Frame(status_frame, bg='#2d2d2d')
        log_frame.pack(fill='both', expand=True)
        
        self.log_text = tk.Text(log_frame, height=12, 
                              bg='#1a1a1a', fg='#00ff41',
                              font=('Consolas', 9),
                              wrap=tk.WORD, state=tk.DISABLED,
                              selectbackground='#404040',
                              insertbackground='#00ff41',
                              relief='flat', bd=0)
        
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y", padx=(0, 5), pady=5)
        
    def log_system_message(self, message, color='#00ff41'):
        """Ghi log thông điệp hệ thống với kiểu dáng terminal"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Bao gồm mili giây
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        
        # Thêm mã màu cho các loại thông điệp khác nhau
        if message.startswith("LỖI_"):
            color = '#ff4444'
        elif message.startswith("CẢNH_BÁO_"):
            color = '#ffaa00'
        elif message.startswith("THÀNH_CÔNG_") or message.startswith("KẾT_NỐI_TC"):
            color = '#44ff44'
        elif message.startswith("HỆ_THỐNG_"):
            color = '#4488ff'
        else:
            color = '#00ff41'
            
        # Chèn với màu (đơn giản hóa cho tkinter cơ bản)
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)
        
    def toggle_system_monitor(self):
        """Chuyển đổi trạng thái giám sát hệ thống"""
        if not self.is_monitoring:
            self.start_system_monitoring()
        else:
            self.stop_system_monitoring()
            
    def start_system_monitoring(self):
        """Bắt đầu quá trình giám sát hệ thống"""
        # Kiểm tra xem tài nguyên có được cấu hình không
        if not self.selected_resource_names:
            self.log_system_message("CẢNH_BÁO_CFG: Vui lòng cấu hình tài nguyên trước khi khởi tạo")
            return
        
        # Xóa vùng log
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        if len(self.selected_resource_names) == 1:
            mode_text = f"Tài nguyên: {self.selected_resource_names[0]}"
        else:
            mode_text = f"Phân bổ động ({len(self.selected_resource_names)} tài nguyên)"
        
        self.log_system_message(f"KHỞI_ĐỘNG_HT: Giám sát hệ thống đã khởi tạo - {mode_text}")
        self.log_system_message("CHỜ_TIẾN_TRÌNH: Đang chờ kích hoạt tiến trình đích...")
        
        # Bắt đầu luồng worker để kiểm tra phân bổ trước
        self.is_monitoring = True
        self.start_button.config(text="⏹️ DỪNG HỆ THỐNG", bg='#ff4444', activebackground='#cc3333')
        
        self.worker_thread = threading.Thread(target=self.system_monitoring_worker, daemon=True)
        self.worker_thread.start()
        
    def stop_system_monitoring(self):
        """Dừng giám sát hệ thống"""
        self.is_monitoring = False
        self.start_button.config(text="⚡ KHỞI TẠO HỆ THỐNG", bg='#00cc44', activebackground='#00b33c')
        self.log_system_message("DỪNG_HT: Giám sát hệ thống đã dừng")
        
    def get_random_resource(self):
        """Lấy tài nguyên tiếp theo trong vòng quay"""
        resources = ["Lux", "Mel"]
        if self.last_allocation is None:
            self.last_allocation = random.choice(resources)
        else:
            # Xoay phiên giữa Lux và Mel
            if self.last_allocation == "Lux":
                self.last_allocation = "Mel"
            else:
                self.last_allocation = "Lux"
        return self.last_allocation
        
    def system_monitoring_worker(self):
        """Luồng worker chính cho giám sát hệ thống và phân bổ tài nguyên"""
        try:
            # Chờ tiến trình đích khởi động
            if not self.wait_for_target_process():
                return
                
            # Chờ xác thực tiến trình
            if not self.wait_for_authentication():
                return
                
            self.log_system_message("THÀNH_CÔNG_XÁC_THỰC: Tiến trình đã được xác thực và thiết lập kết nối hệ thống")
            
            # Lấy tài nguyên đã phân bổ
            if not self.get_allocated_resources():
                self.log_system_message("CẢNH_BÁO_TÀI_NGUYÊN: Không thể truy xuất kho phân bổ tài nguyên")
            
            # Vòng lặp giám sát chính
            resource_idx = 0
            priority_set = False
            
            while self.is_monitoring:
                try:
                    # Lấy giai đoạn tiến trình
                    r = self.request('get', '/lol-gameflow/v1/gameflow-phase')
                    if r.status_code != 200:
                        sleep(1)
                        continue
                        
                    phase = r.json()
                    
                    # Tự động chấp nhận yêu cầu tiến trình
                    if phase == 'ReadyCheck':
                        self.log_system_message("PHÁT_HIỆN_YC: Đã phát hiện yêu cầu tiến trình - đang chấp nhận...")
                        r = self.request('post', '/lol-matchmaking/v1/ready-check/accept')
                        if r.status_code == 204:
                            self.log_system_message("CHẤP_NHẬN_YC: Yêu cầu tiến trình đã được chấp nhận")
                    
                    # Xử lý phân bổ tài nguyên
                    elif phase == 'ChampSelect':
                        self.handle_resource_allocation()
                        
                    elif phase == 'InProgress':
                        if not priority_set:
                            self.set_process_priority()
                            priority_set = True
                        self.log_system_message("TIẾN_TRÌNH_HOẠT_ĐỘNG: Tiến trình đang thực thi")
                        
                    elif phase in ['Matchmaking', 'Lobby', 'None']:
                        priority_set = False
                        
                    sleep(1)
                    
                except Exception as e:
                    self.log_system_message(f"LỖI_GIÁM_SÁT: Lỗi giám sát - {str(e)}")
                    sleep(2)
                    
        except Exception as e:
            self.log_system_message(f"LỖI_NGHIÊM_TRỌNG: Lỗi hệ thống nghiêm trọng - {str(e)}")
        finally:
            if self.is_monitoring:
                self.root.after(0, self.stop_system_monitoring)
                
    def handle_resource_allocation(self):
        """Xử lý giai đoạn phân bổ tài nguyên hệ thống"""
        try:
            r = self.request('get', '/lol-champ-select/v1/session')
            if r.status_code != 200:
                return
                
            session_data = r.json()
            
            # Lấy ID phiên hiện tại để theo dõi các phiên khác nhau
            try:
                session_id = str(session_data.get('gameId', 0))
                if not session_id or session_id == '0':
                    session_id = str(session_data.get('timer', {}).get('adjustedTimeLeftInPhase', 0))
            except:
                session_id = "không_rõ"
            
            # Kiểm tra xem đây có phải là phiên mới không
            if self.current_process_session != session_id:
                self.current_process_session = session_id
                self.has_allocated_in_session = False
            
            # Nếu đã phân bổ trong phiên này, không phân bổ lại
            if self.has_allocated_in_session:
                return
                
            actor_cell_id = -1
            
            # Tìm ID ô tiến trình của chúng ta
            for member in session_data['myTeam']:
                if member['summonerId'] == self.process_id:
                    actor_cell_id = member['cellId']
                    
            if actor_cell_id == -1:
                return
                
            # Kiểm tra hành động phân bổ
            for action in session_data['actions'][0]:
                if action['actorCellId'] != actor_cell_id:
                    continue
                    
                if action['championId'] == 0:  # Chưa phân bổ
                    # Xác định tài nguyên nào để phân bổ - sử dụng ngẫu nhiên thực từ tài nguyên đã chọn
                    if self.selected_resource_names:
                        resource_name = random.choice(self.selected_resource_names)
                        self.log_system_message(f"LỰA_CHỌN_PHÂN_BỔ: Phân bổ động đã chọn: {resource_name}")
                    else:
                        # Fallback cho logic cũ nếu không có tài nguyên được chọn
                        selected = self.selected_resource.get()
                        if selected == "Ngẫu_nhiên":
                            resource_name = self.get_random_resource()
                        else:
                            resource_name = selected
                        
                    resource_id = self.resource_ids.get(resource_name)
                    if not resource_id:
                        self.log_system_message(f"LỖI_TÀI_NGUYÊN: Không tìm thấy ID tài nguyên {resource_name} trong bảng phân bổ")
                        return
                    
                    # Kiểm tra xem tài nguyên có được phân bổ không
                    if self.allocated_resources and resource_id not in self.allocated_resources:
                        self.log_system_message(f"LỖI_KHÔNG_CÓ: Tài nguyên {resource_name} không có sẵn trong kho hiện tại")
                        return
                    
                    # Xử lý đếm ngược độ trễ thực thi
                    try:
                        delay = int(self.execution_delay.get())
                        if delay > 0:
                            for i in range(delay, 0, -1):
                                if not self.is_monitoring:
                                    return
                                self.log_system_message(f"ĐỘ_TRỄ_THỰC_THI: Đếm ngược phân bổ {i}ms cho {resource_name}...")
                                sleep(1)
                    except ValueError:
                        delay = 0  # Nếu đầu vào không hợp lệ, sử dụng độ trễ 0
                    
                    # Phân bổ tài nguyên sử dụng điểm cuối đúng
                    allocation_url = f'/lol-champ-select/v1/session/actions/{action["id"]}'
                    allocation_data = {'championId': resource_id, 'completed': False}
                    
                    self.log_system_message(f"THỰC_THI_PHÂN_BỔ: Đang thực thi phân bổ tài nguyên cho {resource_name}...")
                    
                    r = self.request('patch', allocation_url, '', allocation_data)
                    if r.status_code == 204:
                        self.log_system_message(f"THÀNH_CÔNG_PHÂN_BỔ: Tài nguyên {resource_name} đã được phân bổ thành công")
                        
                        # Đánh dấu là đã phân bổ trong phiên hiện tại để tránh phân bổ lại
                        self.has_allocated_in_session = True
                        
                        # Tự động khóa nếu được bật - sử dụng PATCH với completed: true
                        if self.auto_execute.get():
                            # Thêm độ trễ để đảm bảo phân bổ được xử lý
                            sleep(0.3)
                            
                            self.log_system_message(f"THỰC_THI_KHÓA: Đang thực thi tự động khóa cho {resource_name}...")
                            
                            try:
                                # Sử dụng cùng điểm cuối với completed: true để khóa
                                lock_data = {"championId": resource_id, "completed": True}
                                lock_response = self.request('patch', allocation_url, '', lock_data)
                                
                                if lock_response.status_code == 204:
                                    self.log_system_message(f"THÀNH_CÔNG_KHÓA: Tài nguyên {resource_name} đã được khóa thành công")
                                else:
                                    self.log_system_message(f"CẢNH_BÁO_KHÓA: Khóa tài nguyên {resource_name} thất bại - Trạng thái: {lock_response.status_code}")
                                        
                            except Exception as e:
                                self.log_system_message(f"LỖI_KHÓA: Lỗi kết nối khóa cho {resource_name}: {str(e)}")
                    else:
                        self.log_system_message(f"LỖI_PHÂN_BỔ: Phân bổ tài nguyên {resource_name} thất bại - Trạng thái: {r.status_code}")
                        if r.text:
                            self.log_system_message(f"CHI_TIẾT_LỖI: Chi tiết lỗi phân bổ: {r.text}")
                        
        except Exception as e:
            self.log_system_message(f"LỖI_XỬ_LÝ: Lỗi xử lý phân bổ tài nguyên: {str(e)}")
            
    def detect_target_process(self):
        """Phát hiện đường dẫn cài đặt tiến trình đích từ tiến trình LeagueClientUx.exe đang chạy"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if proc.info['name'] == 'LeagueClientUx.exe':
                        exe_path = proc.info['exe']
                        if exe_path:
                            # Trích xuất thư mục cài đặt
                            process_dir = os.path.dirname(exe_path)
                            return process_dir
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            self.log_system_message(f"LỖI_PHÁT_HIỆN: Lỗi phát hiện tiến trình: {str(e)}")
        return None

    def wait_for_target_process(self):
        """Chờ tiến trình đích khởi động bằng cách phát hiện tiến trình LeagueClientUx.exe"""
        self.log_system_message("QUÉT_TIẾN_TRÌNH: Đang quét kích hoạt tiến trình đích...")
        
        while self.is_monitoring:
            # Thử phát hiện đường dẫn cài đặt tiến trình
            process_dir = self.detect_target_process()
            
            if process_dir:
                lockpath = os.path.join(process_dir, 'lockfile')
                if os.path.isfile(lockpath):
                    try:
                        with open(lockpath, 'r') as f:
                            lockdata = f.read()
                        
                        lock = lockdata.split(':')
                        self.protocol = lock[4]
                        self.port = lock[2]
                        username = 'riot'
                        password = lock[3]
                        
                        # Thiết lập phiên
                        userpass = b64encode(f'{username}:{password}'.encode()).decode('ascii')
                        self.headers = {'Authorization': f'Basic {userpass}'}
                        self.session = requests.session()
                        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                        
                        return True
                    except Exception as e:
                        self.log_system_message(f"LỖI_LOCKFILE: Lỗi xử lý lockfile: {str(e)}")
                else:
                    self.log_system_message("TIẾN_TRÌNH_MỘT_PHẦN: Đã phát hiện tiến trình nhưng lockfile không khả dụng, đang chờ...")
            
            sleep(2)
        return False
        
    def wait_for_authentication(self):
        """Chờ xác thực thành công"""
        while self.is_monitoring:
            try:
                r = self.request('get', '/lol-login/v1/session')
                if r.status_code == 200:
                    session_data = r.json()
                    if session_data['state'] == 'SUCCEEDED':
                        self.process_id = session_data['summonerId']
                        return True
                    else:
                        self.log_system_message(f"TIẾN_TRÌNH_XÁC_THỰC: Xác thực đang tiến hành... ({session_data['state']})")
            except Exception:
                pass
            sleep(1)
        return False
        
    def request(self, method, path, query='', data=''):
        """Thực hiện yêu cầu API đến điểm cuối tiến trình"""
        if not query:
            url = f'{self.protocol}://{self.host}:{self.port}{path}'
        else:
            url = f'{self.protocol}://{self.host}:{self.port}{path}?{query}'
            
        fn = getattr(self.session, method)
        
        if not data:
            r = fn(url, verify=False, headers=self.headers)
        else:
            r = fn(url, verify=False, headers=self.headers, json=data)
            
        return r
        
    def get_allocated_resources(self):
        """Lấy danh sách tài nguyên đã phân bổ - Kiểm tra tương thích hệ thống"""
        try:
            # Thử các điểm cuối API khác nhau để xác thực dữ liệu tài nguyên
            endpoints = [
                '/lol-champions/v1/owned-champions-minimal',
                '/lol-champions/v1/inventories/1/champions-minimal', 
                '/lol-champions/v1/inventories/1/champions',
                '/lol-champions/v1/inventories/CHAMPION/champions',
                '/lol-collections/v1/inventories/CHAMPION'
            ]
            
            self.allocated_resources = []
            
            for endpoint in endpoints:
                try:
                    r = self.request('get', endpoint)
                    if r.status_code == 200:
                        allocated = r.json()
                        if isinstance(allocated, list):
                            # Trích xuất ID tài nguyên từ các định dạng phản hồi khác nhau
                            for resource in allocated:
                                if isinstance(resource, dict):
                                    # Thử các khóa có thể cho ID tài nguyên
                                    resource_id = resource.get('id') or resource.get('championId') or resource.get('itemId')
                                    if resource_id and resource.get('active', True):
                                        self.allocated_resources.append(resource_id)
                        elif isinstance(allocated, dict) and 'champions' in allocated:
                            # Xử lý định dạng phản hồi lồng nhau
                            for resource in allocated['champions']:
                                resource_id = resource.get('id') or resource.get('championId') or resource.get('itemId')
                                if resource_id and resource.get('active', True):
                                    self.allocated_resources.append(resource_id)
                        
                        if self.allocated_resources:
                            self.log_system_message(f"KÍCH_THƯỚC_KHO: Kho phân bổ tài nguyên chứa {len(self.allocated_resources)} tài nguyên")
                            break
                            
                except Exception as e:
                    self.log_system_message(f"CẢNH_BÁO_ĐIỂM_CUỐI: Xác thực điểm cuối {endpoint} thất bại: {str(e)}")
                    continue
            
            # Kiểm tra phân bổ tài nguyên đã chọn với logic cải tiến
            if self.selected_resource_names and len(self.selected_resource_names) > 1:
                # Nhiều tài nguyên được chọn cho phân bổ động - hiển thị thông điệp kết hợp
                self.log_system_message(f"SẴN_SÀNG_PHÂN_BỔ: Đang chờ giai đoạn phân bổ cho kho động ({len(self.selected_resource_names)} tài nguyên)...")
            elif self.selected_resource_names and len(self.selected_resource_names) == 1:
                # Tài nguyên đơn - kiểm tra phân bổ
                resource_name = self.selected_resource_names[0]
                is_allocated = self.check_resource_allocation_improved(resource_name)
                if not is_allocated:
                    return False
                else:
                    self.log_system_message(f"SẴN_SÀNG_PHÂN_BỔ: Đang chờ giai đoạn phân bổ cho tài nguyên {resource_name}...")
            else:
                # Fallback cho logic cũ cho lựa chọn không ngẫu nhiên
                selected = self.selected_resource.get()
                if selected and selected != "Ngẫu_nhiên":
                    is_allocated = self.check_resource_allocation_improved(selected)
                    if not is_allocated:
                        return False
                    else:
                        self.log_system_message(f"SẴN_SÀNG_PHÂN_BỔ: Đang chờ giai đoạn phân bổ cho tài nguyên {selected}...")
                    
            return True
            
        except Exception as e:
            self.log_system_message(f"LỖI_KHO: Lỗi truy xuất kho tài nguyên: {str(e)}")
            # Tiếp tục mà không kiểm tra phân bổ nhưng cảnh báo người dùng
            self.log_system_message("CẢNH_BÁO_BỎ_QUA: Tiếp tục với phân bổ trực tiếp mà không xác thực kho")
            self.allocated_resources = []
            return True

    def check_resource_allocation_improved(self, resource_name):
        """Kiểm tra phân bổ tài nguyên cải tiến cho tương thích hệ thống"""
        try:
            # Đầu tiên thử tìm tài nguyên theo tên trong tất cả tài nguyên có sẵn
            correct_id = self.find_resource_id_by_name(resource_name)
            
            if correct_id:
                self.resource_ids[resource_name] = correct_id
                
                # Kiểm tra xem chúng ta có phân bổ tài nguyên này không
                if correct_id in self.allocated_resources:
                    self.log_system_message(f"XÁC_NHẬN_TÀI_NGUYÊN: Đã xác nhận phân bổ tài nguyên {resource_name}")
                    return True
            
            # Fallback: Kiểm tra ID chính và thay thế
            primary_id = self.resource_ids.get(resource_name)
            if primary_id and primary_id in self.allocated_resources:
                self.log_system_message(f"XÁC_NHẬN_TÀI_NGUYÊN: Đã xác nhận phân bổ tài nguyên {resource_name}")
                return True
            
            # Kiểm tra ID thay thế nếu có sẵn
            alt_ids = self.alternative_resource_ids.get(resource_name, [])
            for alt_id in alt_ids:
                if alt_id in self.allocated_resources:
                    self.log_system_message(f"XÁC_NHẬN_TÀI_NGUYÊN: Đã xác nhận phân bổ tài nguyên {resource_name}")
                    self.resource_ids[resource_name] = alt_id
                    return True
            
            # Phương án cuối cùng: Thử gọi API trực tiếp
            try:
                if primary_id:
                    r = self.request('get', f'/lol-champions/v1/champions/{primary_id}')
                    if r.status_code == 200:
                        resource_info = r.json()
                        if resource_info.get('ownership', {}).get('owned', False):
                            self.log_system_message(f"XÁC_NHẬN_API: Đã xác nhận phân bổ tài nguyên {resource_name} qua API")
                            return True
            except:
                pass
            
            # Nếu không tìm thấy phân bổ, hiển thị thông tin gỡ lỗi chi tiết
            self.log_system_message(f"LỖI_CHƯA_PHÂN_BỔ: Không tìm thấy tài nguyên {resource_name} trong kho phân bổ")
            self.log_system_message(f"TRẠNG_THÁI_KHO: Tổng tài nguyên đã phân bổ: {len(self.allocated_resources)}")
            
            self.root.after(0, self.stop_system_monitoring)
            return False
            
        except Exception as e:
            self.log_system_message(f"LỖI_KIỂM_TRA_PHÂN_BỔ: Lỗi kiểm tra phân bổ tài nguyên cho {resource_name}: {str(e)}")
            return False

    def find_resource_id_by_name(self, resource_name):
        """Tìm ID tài nguyên bằng cách tìm kiếm qua tất cả tài nguyên có sẵn"""
        try:
            # Thử các điểm cuối khác nhau để lấy tất cả tài nguyên
            endpoints = [
                '/lol-champions/v1/champions',
                '/lol-game-data/assets/v1/champions.json',
                '/lol-champions/v1/champions-minimal'
            ]
            
            for endpoint in endpoints:
                try:
                    r = self.request('get', endpoint)
                    if r.status_code == 200:
                        resources_data = r.json()
                        
                        if isinstance(resources_data, list):
                            for resource in resources_data:
                                if isinstance(resource, dict):
                                    resource_name_api = resource.get('name', '').lower()
                                    if resource_name.lower() in resource_name_api or resource_name_api in resource_name.lower():
                                        resource_id = resource.get('id') or resource.get('championId')
                                        if resource_id:
                                            return resource_id
                        elif isinstance(resources_data, dict):
                            # Xử lý dữ liệu lồng nhau
                            for key, resource in resources_data.items():
                                if isinstance(resource, dict):
                                    resource_name_api = resource.get('name', '').lower()
                                    if resource_name.lower() in resource_name_api or resource_name_api in resource_name.lower():
                                        resource_id = resource.get('id') or resource.get('championId') or key
                                        if resource_id and str(resource_id).isdigit():
                                            return int(resource_id)
                                            
                except Exception:
                    continue
                    
            return None
            
        except Exception as e:
            self.log_system_message(f"CẢNH_BÁO_TÌM_KIẾM: Lỗi tìm kiếm ID tài nguyên: {str(e)}")
            return None

    def set_process_priority(self):
        """Đặt ưu tiên cao cho tiến trình đích"""
        try:
            for p in psutil.process_iter():
                try:
                    if p.name() == 'League of Legends.exe':
                        p.nice(psutil.HIGH_PRIORITY_CLASS)
                        self.log_system_message("ĐẶT_ƯU_TIÊN: Đã gán ưu tiên cao cho tiến trình đích")
                        break
                except (psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception:
            pass

    def open_resource_selection_dialog(self):
        """Mở hộp thoại cấu hình lựa chọn tài nguyên"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Bảng Điều Khiển Cấu Hình Tài Nguyên")
        dialog.geometry("500x550")
        dialog.resizable(False, False)
        dialog.configure(bg='#2d2d2d')
        
        # Xóa biểu tượng cửa sổ cho dialog
        try:
            dialog.iconbitmap('')
        except:
            pass
        
        # Căn giữa dialog
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Lấy tài nguyên có sẵn - tất cả tài nguyên từ danh sách
        available_resources = list(self.resource_ids.keys())
        available_resources.sort()  # Sắp xếp theo thứ tự bảng chữ cái cho trải nghiệm người dùng tốt hơn
        
        # Tạo biến tài nguyên trước
        resource_vars = {}
        for resource in available_resources:
            var = tk.BooleanVar(value=resource in self.selected_resource_names)
            resource_vars[resource] = var
        
        # Khung chính
        main_frame = tk.Frame(dialog, bg='#2d2d2d')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Tiêu đề
        title_label = tk.Label(main_frame, text="🔧 Bảng Điều Khiển Cấu Hình Tài Nguyên", 
                             bg='#2d2d2d', fg='#00d4aa', font=('Segoe UI', 14, 'bold'))
        title_label.pack(pady=(0, 15))
        
        # Khung nút điều khiển
        control_frame = tk.Frame(main_frame, bg='#2d2d2d')
        control_frame.pack(fill='x', pady=(0, 10))
        
        select_all_btn = tk.Button(control_frame, text="Chọn Tất Cả",
                                 command=lambda: self.select_all_resources(resource_vars),
                                 font=('Segoe UI', 10), bg='#00cc44', fg='white',
                                 activebackground='#00b33c', relief='raised', bd=2)
        select_all_btn.pack(side='left')
        
        deselect_all_btn = tk.Button(control_frame, text="Xóa Tất Cả",
                                   command=lambda: self.deselect_all_resources(resource_vars),
                                   font=('Segoe UI', 10), bg='#ff4444', fg='white',
                                   activebackground='#cc3333', relief='raised', bd=2)
        deselect_all_btn.pack(side='left', padx=(10, 0))
        
        # Khung danh sách tài nguyên với thanh cuộn
        list_frame = tk.Frame(main_frame, bg='#2d2d2d')
        list_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        # Canvas và thanh cuộn cho danh sách tài nguyên
        canvas = tk.Canvas(list_frame, bg='#404040', highlightthickness=0, height=120)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#404040')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bật cuộn chuột
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind('<Enter>', _bind_mousewheel)
        canvas.bind('<Leave>', _unbind_mousewheel)
        
        # Tạo checkbox tài nguyên
        for i, resource in enumerate(available_resources):
            var = resource_vars[resource]
            
            cb = tk.Checkbutton(scrollable_frame, text=resource, variable=var,
                              bg='#404040', fg='#ffffff', font=('Segoe UI', 11),
                              activebackground='#555555', selectcolor='#0066cc',
                              anchor='w', padx=5)
            cb.pack(anchor='w', padx=10, pady=5, fill='x')
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Thông tin lựa chọn
        info_frame = tk.Frame(main_frame, bg='#2d2d2d')
        info_frame.pack(fill='x', pady=(0, 15))
        
        info_label = tk.Label(info_frame, text="💡 Cấu hình tài nguyên cho phân bổ động. Đối với kho >3 tài nguyên, hệ thống sẽ yêu cầu xác nhận.",
                            bg='#2d2d2d', fg='#ff9500', font=('Segoe UI', 9), wraplength=400)
        info_label.pack()
        
        # Nút dưới cùng
        button_frame = tk.Frame(main_frame, bg='#2d2d2d')
        button_frame.pack(fill='x', pady=(10, 0))
        
        # Nút hủy bên trái
        cancel_btn = tk.Button(button_frame, text="❌ HỦY",
                             command=dialog.destroy,
                             font=('Segoe UI', 11), bg='#ff4444', fg='white',
                             activebackground='#cc3333', relief='raised', bd=3, padx=20, pady=5)
        cancel_btn.pack(side='left')
        
        # Nút xác nhận bên phải - làm nổi bật hơn
        confirm_btn = tk.Button(button_frame, text="✅ ÁP DỤNG CẤU HÌNH",
                              command=lambda: self.confirm_resource_selection(dialog, resource_vars, available_resources),
                              font=('Segoe UI', 11, 'bold'), bg='#00cc44', fg='white',
                              activebackground='#00b33c', relief='raised', bd=4, padx=25, pady=8)
        confirm_btn.pack(side='right')
        
    def select_all_resources(self, resource_vars):
        """Chọn tất cả tài nguyên trong dialog"""
        for var in resource_vars.values():
            var.set(True)
    
    def deselect_all_resources(self, resource_vars):
        """Bỏ chọn tất cả tài nguyên trong dialog"""
        for var in resource_vars.values():
            var.set(False)
    
    def confirm_resource_selection(self, dialog, resource_vars, available_resources):
        """Xác nhận lựa chọn tài nguyên và cập nhật hiển thị"""
        selected = [resource for resource, var in resource_vars.items() if var.get()]
        
        if not selected:
            messagebox.showwarning("Cảnh Báo Cấu Hình", "Vui lòng cấu hình ít nhất một tài nguyên!")
            return
        
        # Đóng dialog cấu hình trước
        dialog.destroy()
        
        # Xử lý lựa chọn tài nguyên đơn
        if len(selected) == 1:
            resource = selected[0]
            self.selected_resource_names = selected
            self.update_resources_display()
            
            # Kiểm tra phân bổ ngay lập tức cho tài nguyên đơn
            if self.is_connected and self.session and self.headers:
                self.check_single_resource_allocation(resource)
            else:
                self.log_system_message(f"ĐẶT_CẤU_HÌNH: Đã cấu hình tài nguyên {resource}. Kết nối với hệ thống để xác thực phân bổ.")
        
        # Xử lý lựa chọn nhiều tài nguyên
        else:
            self.selected_resource_names = selected
            self.update_resources_display()
            
            if self.is_connected and self.session and self.headers:
                # Hiển thị đang tải và kiểm tra tất cả tài nguyên
                self.check_multiple_resources_allocation(selected)
            else:
                if len(selected) <= 3:
                    self.log_system_message(f"ĐẶT_CẤU_HÌNH: Đã cấu hình {len(selected)} tài nguyên: {', '.join(selected)}")
                else:
                    self.log_system_message(f"ĐẶT_CẤU_HÌNH: Đã cấu hình {len(selected)} tài nguyên cho phân bổ động")
                self.log_system_message("SẴN_SÀNG_HỆ_THỐNG: Kết nối với hệ thống để xác thực phân bổ")
    
    def update_resources_display(self):
        """Cập nhật hiển thị tài nguyên"""
        if not self.selected_resource_names:
            self.resources_label.config(text="Chưa cấu hình tài nguyên")
            return
        
        # Xử lý các trường hợp hiển thị khác nhau dựa trên số lượng tài nguyên
        resource_count = len(self.selected_resource_names)
        
        if resource_count == 1:
            display_text = f"Đã cấu hình: {self.selected_resource_names[0]}"
        elif resource_count <= 3:
            display_text = f"Kho động ({resource_count}): {', '.join(self.selected_resource_names)}"
        else:
            first_three = ', '.join(self.selected_resource_names[:3])
            remaining = resource_count - 3
            display_text = f"Kho động ({resource_count}): {first_three}... (+{remaining} khác)"
        
        self.resources_label.config(text=display_text)
    
    def check_single_resource_allocation(self, resource_name):
        """Kiểm tra phân bổ cho tài nguyên đơn"""
        try:
            # Lấy tài nguyên đã phân bổ trước
            allocated_resources = self.get_allocated_resources_list()
            if not allocated_resources:
                self.log_system_message(f"CẢNH_BÁO_XÁC_THỰC: Không thể xác thực tài nguyên {resource_name}")
                return
                
            # Kiểm tra phân bổ
            primary_id = self.resource_ids.get(resource_name)
            alt_ids = self.alternative_resource_ids.get(resource_name, [])
            all_ids_to_check = [primary_id] + alt_ids if primary_id else alt_ids
            
            resource_found = False
            for resource_id in all_ids_to_check:
                if resource_id and resource_id in allocated_resources:
                    resource_found = True
                    break
                    
            if resource_found:
                self.log_system_message(f"ĐÃ_XÁC_THỰC_TÀI_NGUYÊN: Đã xác thực phân bổ tài nguyên {resource_name}")
            else:
                self.log_system_message(f"LỖI_XÁC_THỰC: Không tìm thấy tài nguyên {resource_name} trong kho phân bổ hiện tại")
                
        except Exception as e:
            self.log_system_message(f"LỖI_XÁC_THỰC: Lỗi xác thực tài nguyên {resource_name}: {str(e)}")
    
    def check_multiple_resources_allocation(self, resources_list):
        """Kiểm tra phân bổ cho nhiều tài nguyên với đang tải"""
        # Hiển thị đang tải
        self.loading_frame.pack(pady=(10, 0))
        
        # Bắt đầu kiểm tra trong luồng nền
        check_thread = threading.Thread(target=self._check_resources_thread, args=(resources_list,), daemon=True)
        check_thread.start()
    
    def _check_resources_thread(self, resources_list):
        """Luồng nền để kiểm tra phân bổ tài nguyên"""
        try:
            # Lấy tài nguyên đã phân bổ
            allocated_resources = self.get_allocated_resources_list()
            if not allocated_resources:
                self.root.after(0, self._hide_loading)
                self.root.after(0, lambda: self.log_system_message("CẢNH_BÁO_XÁC_THỰC: Không thể xác thực kho tài nguyên"))
                return
            
            # Kiểm tra từng tài nguyên
            missing_resources = []
            for resource_name in resources_list:
                primary_id = self.resource_ids.get(resource_name)
                alt_ids = self.alternative_resource_ids.get(resource_name, [])
                all_ids_to_check = [primary_id] + alt_ids if primary_id else alt_ids
                
                resource_found = False
                for resource_id in all_ids_to_check:
                    if resource_id and resource_id in allocated_resources:
                        resource_found = True
                        break
                        
                if not resource_found:
                    missing_resources.append(resource_name)
            
            # Ẩn đang tải và hiển thị kết quả
            self.root.after(0, self._hide_loading)
            
            if missing_resources:
                # Hiển thị dialog tài nguyên thiếu
                self.root.after(0, lambda: self._show_missing_resources_dialog(missing_resources))
            else:
                # Tất cả tài nguyên đã được phân bổ
                if len(resources_list) <= 3:
                    self.root.after(0, lambda: self.log_system_message(f"ĐÃ_XÁC_THỰC_KHO: Kho động đã được cấu hình thành công: {', '.join(resources_list)}"))
                else:
                    self.root.after(0, lambda: self.log_system_message(f"ĐÃ_XÁC_THỰC_KHO: Kho động đã được cấu hình thành công ({len(resources_list)} tài nguyên)"))
                    
        except Exception as e:
            self.root.after(0, self._hide_loading)
            self.root.after(0, lambda: self.log_system_message(f"LỖI_XÁC_THỰC: Lỗi xác thực kho: {str(e)}"))
    
    def _hide_loading(self):
        """Ẩn chỉ báo đang tải"""
        self.loading_frame.pack_forget()
    
    def _show_missing_resources_dialog(self, missing_resources):
        """Hiển thị dialog cho tài nguyên thiếu"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Cảnh Báo Xác Thực Tài Nguyên")
        dialog.geometry("450x220")
        dialog.resizable(False, False)
        dialog.configure(bg='#2d2d2d')
        
        # Xóa biểu tượng cửa sổ
        try:
            dialog.iconbitmap('')
        except:
            pass
        
        # Căn giữa dialog
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Khung chính
        main_frame = tk.Frame(dialog, bg='#2d2d2d')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Biểu tượng cảnh báo và tiêu đề
        title_frame = tk.Frame(main_frame, bg='#2d2d2d')
        title_frame.pack(pady=(0, 15))
        
        title_label = tk.Label(title_frame, text="⚠️ Cảnh Báo Phân Bổ Tài Nguyên", 
                             bg='#2d2d2d', fg='#ff4444', font=('Segoe UI', 14, 'bold'))
        title_label.pack()
        
        # Thông điệp
        missing_text = ', '.join(missing_resources)
        message_text = f"Tài nguyên {missing_text} không tìm thấy trong kho phân bổ hiện tại. Hệ thống sẽ tự động loại bỏ khỏi cấu hình.\n\nCấu hình lại kho sau khi có thêm tài nguyên."
        
        message_label = tk.Label(main_frame, text=message_text,
                               bg='#2d2d2d', fg='#ffffff', font=('Segoe UI', 10),
                               wraplength=400, justify='center')
        message_label.pack(pady=(0, 20))
        
        # Nút đóng
        close_btn = tk.Button(main_frame, text="XÁC NHẬN",
                            command=lambda: self._close_missing_dialog(dialog, missing_resources),
                            font=('Segoe UI', 11, 'bold'), bg='#0066cc', fg='white',
                            activebackground='#0052a3', relief='raised', bd=3,
                            padx=30, pady=8)
        close_btn.pack()
    
    def _close_missing_dialog(self, dialog, missing_resources):
        """Đóng dialog tài nguyên thiếu và cập nhật lựa chọn"""
        dialog.destroy()
        
        # Loại bỏ tài nguyên thiếu khỏi lựa chọn
        remaining_resources = [res for res in self.selected_resource_names if res not in missing_resources]
        self.selected_resource_names = remaining_resources
        
        # Cập nhật hiển thị
        self.update_resources_display()
        
        # Ghi log cập nhật
        if remaining_resources:
            if len(remaining_resources) <= 3:
                self.log_system_message(f"CẬP_NHẬT_KHO: Cấu hình đã được cập nhật: {', '.join(remaining_resources)}")
            else:
                self.log_system_message(f"CẬP_NHẬT_KHO: Cấu hình đã được cập nhật ({len(remaining_resources)} tài nguyên)")
        else:
            self.log_system_message("CẤU_HÌNH_TRỐNG: Không còn tài nguyên nào. Vui lòng cấu hình lại kho phân bổ!")
    
    def get_allocated_resources_list(self):
        """Lấy danh sách ID tài nguyên đã phân bổ"""
        try:
            endpoints = [
                '/lol-champions/v1/owned-champions-minimal',
                '/lol-champions/v1/inventories/1/champions-minimal',
                '/lol-champions/v1/inventories/1/champions',
                '/lol-champions/v1/inventories/CHAMPION/champions',
                '/lol-collections/v1/inventories/CHAMPION'
            ]
            
            for endpoint in endpoints:
                try:
                    r = self.request('get', endpoint)
                    if r.status_code == 200:
                        allocated = r.json()
                        allocated_resources = []
                        
                        if isinstance(allocated, list):
                            for resource in allocated:
                                if isinstance(resource, dict):
                                    resource_id = resource.get('id') or resource.get('championId') or resource.get('itemId')
                                    if resource_id and resource.get('active', True):
                                        allocated_resources.append(resource_id)
                        elif isinstance(allocated, dict) and 'champions' in allocated:
                            for resource in allocated['champions']:
                                resource_id = resource.get('id') or resource.get('championId') or resource.get('itemId')
                                if resource_id and resource.get('active', True):
                                    allocated_resources.append(resource_id)
                        
                        if allocated_resources:
                            return allocated_resources
                except Exception:
                    continue
            
            return []
        except Exception:
            return []
    
    def get_random_resource_from_selected(self):
        """Lấy tài nguyên ngẫu nhiên từ danh sách đã chọn"""
        if not self.selected_resource_names:
            # Fallback cho hành vi gốc nếu không có tài nguyên được chọn
            return self.get_random_resource()
        
        return random.choice(self.selected_resource_names)


def main():
    root = tk.Tk()
    app = SystemProcessManager(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        if app.is_monitoring:
            app.stop_system_monitoring()
        root.quit()


if __name__ == "__main__":
    main()
