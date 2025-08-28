###############################################################################
# League of Legends Auto Pick GUI
# Beautiful interface for auto picking champions
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

class AutoPickLOLGUI:
    def __init__(self, root):
        self.root = root
        self.setup_window()
        self.setup_variables()
        self.setup_styles()
        self.create_widgets()
        
        # Game connection variables
        self.is_running = False
        self.session = None
        self.headers = None
        self.protocol = None
        self.host = '127.0.0.1'
        self.port = None
        self.summoner_id = None
        self.worker_thread = None
        
        # Champion data - Updated for 2025 with full champion list
        self.champions = {
            "99": "Lux", "800": "Mel", "54": "Malphite", "84": "Akali", 
            "53": "Blitzcrank", "245": "Ekko", "3": "Galio", "555": "Pyke",
            "254": "Vi", "234": "Viego", "134": "Syndra", "517": "Sylas",
            "59": "Jarvan IV", "12": "Alistar", "64": "Lee Sin", "7": "LeBlanc",
            "110": "Varus", "121": "Kha'Zix", "105": "Fizz", "126": "Jayce"
        }
        self.champion_ids = {
            "Lux": 99, "Mel": 800, "Malphite": 54, "Akali": 84,
            "Blitzcrank": 53, "Ekko": 245, "Galio": 3, "Pyke": 555,
            "Vi": 254, "Viego": 234, "Syndra": 134, "Sylas": 517,
            "Jarvan IV": 59, "Alistar": 12, "Lee Sin": 64, "LeBlanc": 7,
            "Varus": 110, "Kha'Zix": 121, "Fizz": 105, "Jayce": 126
        }
        self.owned_champions = []
        
        # Alternative champion IDs to check (in case of ID changes)
        self.alternative_champion_ids = {
            "Mel": [800, 950, 980, 910]  # Multiple possible IDs for Mel
        }
        
        # Random selection state
        self.last_random_pick = None
        self.random_champions = []  # Selected champions for random picking
        self.random_champion_names = []  # Names of selected champions
        
        # Connection status
        self.is_connected = False
        
        # Game state tracking
        self.current_game_id = None
        self.has_picked_in_current_game = False
        
        # Start background checker
        self.start_background_checker()
        
    def start_background_checker(self):
        """Start background monitoring for League connection"""
        self.log_message("⏳ Đang chờ bạn mở app")
        # Start monitoring thread
        monitoring_thread = threading.Thread(target=self.background_monitor, daemon=True)
        monitoring_thread.start()
        
    def background_monitor(self):
        """Background monitoring for League connection status"""
        while True:
            try:
                # Check if League is running
                league_running = self.detect_league_path() is not None
                
                if league_running and not self.is_connected:
                    # League just started
                    self.is_connected = True
                    self.log_message("✅ Mở app thành công và kết nối thành công")
                    
                    # Try to establish connection
                    league_dir = self.detect_league_path()
                    if league_dir:
                        lockpath = os.path.join(league_dir, 'lockfile')
                        if os.path.isfile(lockpath):
                            try:
                                with open(lockpath, 'r') as f:
                                    lockdata = f.read()
                                
                                lock = lockdata.split(':')
                                self.protocol = lock[4]
                                self.port = lock[2]
                                username = 'riot'
                                password = lock[3]
                                
                                # Setup session
                                userpass = b64encode(f'{username}:{password}'.encode()).decode('ascii')
                                self.headers = {'Authorization': f'Basic {userpass}'}
                                self.session = requests.session()
                                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                                
                                # Auto-check champion ownership when connected (wait for League to fully load)
                                if self.random_champion_names:
                                    if len(self.random_champion_names) == 1:
                                        # Single champion - check after League loads
                                        champion_name = self.random_champion_names[0]
                                        self.root.after(4000, lambda: self.check_single_champion_ownership(champion_name))
                                    else:
                                        # Multiple champions - check with loading after League loads
                                        self.root.after(4000, lambda: self.check_multiple_champions_ownership(self.random_champion_names))
                                
                            except Exception as e:
                                self.log_message(f"❌ Lỗi khi kết nối: {str(e)}")
                                
                elif not league_running and self.is_connected:
                    # League was closed
                    self.is_connected = False
                    self.log_message("⏳ Đang chờ bạn mở app")
                    
            except Exception as e:
                pass  # Silently handle errors in background monitoring
                
            sleep(3)  # Check every 3 seconds
            
    def on_champion_selected(self, event=None):
        """Handle champion selection from combobox"""
        selected = self.selected_champion.get()
        
        if selected == "Random":
            # Show random display and open champion selection dialog
            self.random_display_frame.pack(anchor='w', pady=(5, 0))
            if not self.random_champion_names:
                # First time selecting random, open dialog
                self.open_champion_selection_dialog()
            else:
                # Update display with previously selected champions
                self.update_random_champions_display()
            return
        else:
            # Hide random display for single champion selection
            self.random_display_frame.pack_forget()
            
        if not self.is_connected:
            self.log_message(f"⚠️ Vui lòng mở League of Legends trước khi chọn tướng")
            return
            
        # Check champion ownership immediately
        self.check_champion_ownership(selected)
        
    def check_champion_ownership(self, champion_name):
        """Check if selected champion is owned - Updated for 2025"""
        try:
            if not self.session or not self.headers:
                self.log_message(f"⚠️ Chưa kết nối đến League Client")
                return
                
            # Try different API endpoints for champion data (2025 updated)
            endpoints = [
                '/lol-champions/v1/owned-champions-minimal',
                '/lol-champions/v1/inventories/1/champions-minimal',
                '/lol-champions/v1/inventories/1/champions',
                '/lol-champions/v1/inventories/CHAMPION/champions',  # New endpoint for 2025
                '/lol-collections/v1/inventories/CHAMPION'  # Alternative 2025 endpoint
            ]
            
            owned_champions = []
            
            for endpoint in endpoints:
                try:
                    r = self.request('get', endpoint)
                    if r.status_code == 200:
                        owned = r.json()
                        if isinstance(owned, list):
                            for champ in owned:
                                if isinstance(champ, dict):
                                    champ_id = champ.get('id') or champ.get('championId') or champ.get('itemId')
                                    if champ_id and champ.get('active', True):
                                        owned_champions.append(champ_id)
                        elif isinstance(owned, dict) and 'champions' in owned:
                            for champ in owned['champions']:
                                champ_id = champ.get('id') or champ.get('championId') or champ.get('itemId')
                                if champ_id and champ.get('active', True):
                                    owned_champions.append(champ_id)
                        
                        if owned_champions:
                            break
                except Exception:
                    continue
            
            if not owned_champions:
                self.log_message(f"⚠️ Không thể kiểm tra tướng sở hữu - sẽ thử pick trực tiếp khi bắt đầu")
                return
                
            # Enhanced ownership checking with alternative IDs
            primary_id = self.champion_ids.get(champion_name)
            alt_ids = self.alternative_champion_ids.get(champion_name, [])
            all_ids_to_check = [primary_id] + alt_ids if primary_id else alt_ids
            
            champion_found = False
            found_id = None
            
            for champ_id in all_ids_to_check:
                if champ_id and champ_id in owned_champions:
                    champion_found = True
                    found_id = champ_id
                    # Update primary ID if alternative was found
                    if champ_id != primary_id:
                        self.champion_ids[champion_name] = champ_id
                    break
            
            if champion_found:
                self.log_message(f"✅ Xác nhận có tướng {champion_name}")
            else:
                self.log_message(f"❌ Chưa có tướng {champion_name}")
                self.log_message(f"📋 Tổng {len(owned_champions)} tướng sở hữu")
                
        except Exception as e:
            self.log_message(f"⚠️ Không thể kiểm tra tướng {champion_name}: {str(e)}")
        
    def setup_window(self):
        self.root.title("Auto Pick LOL - JoHan")
        self.root.geometry("500x700")
        self.root.resizable(False, False)
        
        # Remove window icon - try multiple methods
        try:
            self.root.iconbitmap('')
        except:
            try:
                # Alternative method for Windows
                self.root.wm_iconbitmap('')
            except:
                try:
                    # Another alternative - set to None
                    self.root.iconphoto(True, tk.PhotoImage())
                except:
                    pass
        
        # Set window background and center it
        self.root.configure(bg='#0f2027')
        self.center_window()
        
    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def setup_variables(self):
        self.selected_champion = tk.StringVar(value="Lux")
        self.auto_lock = tk.BooleanVar(value=True)
        self.delay_seconds = tk.StringVar(value="0")
        
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure custom styles
        style.configure('Title.TLabel', 
                       background='#0f2027', 
                       foreground='#c9b037',
                       font=('Arial', 24, 'bold'))
        
        style.configure('Subtitle.TLabel',
                       background='#0f2027',
                       foreground='#ffffff',
                       font=('Arial', 12))
        
        style.configure('Custom.TRadiobutton',
                       background='#0f2027',
                       foreground='#ffffff',
                       font=('Arial', 14),
                       focuscolor='none')
        
        style.configure('Custom.TCheckbutton',
                       background='#0f2027',
                       foreground='#ffffff',
                       font=('Arial', 12),
                       focuscolor='none')
        
        style.configure('Start.TButton',
                       font=('Arial', 16, 'bold'),
                       padding=(20, 10))
        
        style.configure('Stop.TButton',
                       font=('Arial', 16, 'bold'),
                       padding=(20, 10))
        
    def create_widgets(self):
        # Main container
        main_frame = tk.Frame(self.root, bg='#0f2027')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Auto Pick LOL - JoHan", style='Title.TLabel')
        title_label.pack(pady=(0, 30))
        
        # Champion selection section
        champion_frame = tk.LabelFrame(main_frame, text="Chọn tướng", 
                                     bg='#203a43', fg='#c9b037', 
                                     font=('Arial', 14, 'bold'), padx=20, pady=15)
        champion_frame.pack(fill='x', pady=(0, 20))
        
        # Champion selection button
        self.select_champion_button = tk.Button(champion_frame, text="🎯 CHỌN TƯỚNG",
                                               command=self.open_champion_selection_dialog,
                                               font=('Arial', 14, 'bold'),
                                               bg='#3498db', fg='white',
                                               activebackground='#2980b9',
                                               relief='raised', bd=3,
                                               padx=20, pady=10)
        self.select_champion_button.pack(pady=(0, 10))
        
        # Selected champions display
        self.champions_display_frame = tk.Frame(champion_frame, bg='#203a43')
        self.champions_display_frame.pack(anchor='w', pady=(5, 0), fill='x')
        
        self.champions_label = tk.Label(self.champions_display_frame, 
                                       text="Chưa chọn tướng nào", bg='#203a43', fg='#ffffff', 
                                       font=('Arial', 11), wraplength=400)
        self.champions_label.pack(side='left', anchor='w')
        
        # Loading indicator
        self.loading_frame = tk.Frame(champion_frame, bg='#203a43')
        self.loading_label = tk.Label(self.loading_frame, 
                                    text="⏳ Đang kiểm tra tướng sở hữu...", 
                                    bg='#203a43', fg='#f39c12', 
                                    font=('Arial', 10))
        self.loading_label.pack()
        
        # Delay setting section
        delay_label = tk.Label(champion_frame, text="Cài giây trễ (s):", 
                             bg='#203a43', fg='#ffffff', font=('Arial', 12))
        delay_label.pack(anchor='w', pady=(5, 5))
        
        delay_entry = tk.Entry(champion_frame, textvariable=self.delay_seconds, 
                             width=10, font=('Arial', 12))
        delay_entry.pack(anchor='w')
        
        # Auto lock section
        lock_frame = tk.LabelFrame(main_frame, text="Tự động khóa tướng", 
                                 bg='#203a43', fg='#c9b037', 
                                 font=('Arial', 14, 'bold'), padx=20, pady=15)
        lock_frame.pack(fill='x', pady=(0, 20))
        
        ttk.Checkbutton(lock_frame, text="Tự động khóa tướng sau khi chọn", 
                       variable=self.auto_lock, style='Custom.TCheckbutton').pack(anchor='w')
        
        # Control buttons
        button_frame = tk.Frame(main_frame, bg='#0f2027')
        button_frame.pack(fill='x', pady=(0, 20))
        
        self.start_button = tk.Button(button_frame, text="BẮT ĐẦU", 
                                    command=self.toggle_auto_pick,
                                    font=('Arial', 16, 'bold'),
                                    bg='#27ae60', fg='white',
                                    activebackground='#2ecc71',
                                    activeforeground='white',
                                    relief='raised',
                                    bd=3, padx=30, pady=10)
        self.start_button.pack()
        
        # Status section
        status_frame = tk.LabelFrame(main_frame, text="Trạng thái", 
                                   bg='#203a43', fg='#c9b037', 
                                   font=('Arial', 14, 'bold'), padx=10, pady=10)
        status_frame.pack(fill='both', expand=True)
        
        # Log text area
        log_frame = tk.Frame(status_frame, bg='#203a43')
        log_frame.pack(fill='both', expand=True)
        
        self.log_text = tk.Text(log_frame, height=15, width=50, 
                              bg='#2c3e50', fg='#ecf0f1',
                              font=('Consolas', 10),
                              wrap=tk.WORD, state=tk.DISABLED)
        
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def log_message(self, message, color='#ecf0f1'):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)
        
    def toggle_auto_pick(self):
        if not self.is_running:
            self.start_auto_pick()
        else:
            self.stop_auto_pick()
            
    def start_auto_pick(self):
        # Check if champions are selected
        if not self.random_champion_names:
            self.log_message("⚠️ Vui lòng chọn tướng trước khi bắt đầu!")
            return
        
        # Clear log area
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        if len(self.random_champion_names) == 1:
            mode_text = f"Tướng: {self.random_champion_names[0]}"
        else:
            mode_text = f"Random {len(self.random_champion_names)} tướng"
        
        self.log_message(f"🎮 Bắt đầu auto pick - {mode_text}")
        self.log_message("⏳ Đang chờ League of Legends khởi động...")
        
        # Start worker thread to check ownership first
        self.is_running = True
        self.start_button.config(text="DỪNG", bg='#e74c3c', activebackground='#c0392b')
        
        self.worker_thread = threading.Thread(target=self.auto_pick_worker, daemon=True)
        self.worker_thread.start()
        
    def stop_auto_pick(self):
        self.is_running = False
        self.start_button.config(text="BẮT ĐẦU", bg='#27ae60', activebackground='#2ecc71')
        self.log_message("⏹️ Đã dừng auto pick")
        
    def get_random_champion(self):
        """Get next champion in random rotation"""
        champions = ["Lux", "Mel"]
        if self.last_random_pick is None:
            import random
            self.last_random_pick = random.choice(champions)
        else:
            # Alternate between Lux and Mel
            if self.last_random_pick == "Lux":
                self.last_random_pick = "Mel"
            else:
                self.last_random_pick = "Lux"
        return self.last_random_pick
        
    def auto_pick_worker(self):
        """Main worker thread for auto picking"""
        try:
            # Wait for League to start
            if not self.wait_for_league():
                return
                
            # Wait for login
            if not self.wait_for_login():
                return
                
            self.log_message("✅ Đã mở app thành công và kết nối thành công")
            
            # Get owned champions
            if not self.get_owned_champions():
                self.log_message("⚠️ Không thể lấy danh sách tướng sở hữu")
            
            # Main loop
            champion_idx = 0
            set_priority = False
            
            while self.is_running:
                try:
                    # Get game phase
                    r = self.request('get', '/lol-gameflow/v1/gameflow-phase')
                    if r.status_code != 200:
                        sleep(1)
                        continue
                        
                    phase = r.json()
                    
                    # Auto accept match
                    if phase == 'ReadyCheck':
                        self.log_message("🔔 Tìm thấy trận đấu - Đang chấp nhận...")
                        r = self.request('post', '/lol-matchmaking/v1/ready-check/accept')
                        if r.status_code == 204:
                            self.log_message("✅ Đã chấp nhận trận đấu")
                    
                    # Pick champion
                    elif phase == 'ChampSelect':
                        self.handle_champion_select()
                        
                    elif phase == 'InProgress':
                        if not set_priority:
                            self.set_game_priority()
                            set_priority = True
                        self.log_message("🎮 Trận đấu đã bắt đầu")
                        
                    elif phase in ['Matchmaking', 'Lobby', 'None']:
                        set_priority = False
                        
                    sleep(1)
                    
                except Exception as e:
                    self.log_message(f"❌ Lỗi: {str(e)}")
                    sleep(2)
                    
        except Exception as e:
            self.log_message(f"❌ Lỗi nghiêm trọng: {str(e)}")
        finally:
            if self.is_running:
                self.root.after(0, self.stop_auto_pick)
                
    def handle_champion_select(self):
        """Handle champion selection phase"""
        try:
            r = self.request('get', '/lol-champ-select/v1/session')
            if r.status_code != 200:
                return
                
            cs = r.json()
            
            # Get current game ID to track different games
            try:
                game_id = str(cs.get('gameId', 0))  # Use gameId from champ select session
                if not game_id or game_id == '0':
                    # Try alternative - use session timer as fallback
                    game_id = str(cs.get('timer', {}).get('adjustedTimeLeftInPhase', 0))
            except:
                game_id = "unknown"
            
            # Check if this is a new game
            if self.current_game_id != game_id:
                self.current_game_id = game_id
                self.has_picked_in_current_game = False
            
            # If already picked in this game, don't pick again
            if self.has_picked_in_current_game:
                return
                
            actor_cell_id = -1
            
            # Find our cell ID
            for member in cs['myTeam']:
                if member['summonerId'] == self.summoner_id:
                    actor_cell_id = member['cellId']
                    
            if actor_cell_id == -1:
                return
                
            # Check actions
            for action in cs['actions'][0]:
                if action['actorCellId'] != actor_cell_id:
                    continue
                    
                if action['championId'] == 0:  # Haven't picked yet
                    # Determine which champion to pick - use true random from selected champions
                    if self.random_champion_names:
                        champion_name = random.choice(self.random_champion_names)
                        self.log_message(f"🎲 Random chọn: {champion_name}")
                    else:
                        # Fallback to old logic if no champions selected
                        selected = self.selected_champion.get()
                        if selected == "Random":
                            champion_name = self.get_random_champion()
                        else:
                            champion_name = selected
                        
                    champion_id = self.champion_ids.get(champion_name)
                    if not champion_id:
                        self.log_message(f"❌ Không tìm thấy ID của tướng {champion_name}!")
                        return
                    
                    # Check if champion is owned
                    if self.owned_champions and champion_id not in self.owned_champions:
                        self.log_message(f"❌ Bạn không sở hữu tướng {champion_name}!")
                        return
                    
                    # Handle delay countdown
                    try:
                        delay = int(self.delay_seconds.get())
                        if delay > 0:
                            for i in range(delay, 0, -1):
                                if not self.is_running:
                                    return
                                self.log_message(f"⏰ Đếm ngược {i} giây trước khi pick {champion_name}...")
                                sleep(1)
                    except ValueError:
                        delay = 0  # If invalid input, use 0 delay
                    
                    # Pick champion using correct champ-select endpoint
                    pick_url = f'/lol-champ-select/v1/session/actions/{action["id"]}'
                    pick_data = {'championId': champion_id, 'completed': False}
                    
                    self.log_message(f"🎯 Đang chọn tướng {champion_name}...")
                    
                    r = self.request('patch', pick_url, '', pick_data)
                    if r.status_code == 204:
                        self.log_message(f"✅ Đã chọn {champion_name} thành công!")
                        
                        # Mark as picked in current game to avoid picking again
                        self.has_picked_in_current_game = True
                        
                        # Auto lock if enabled - use PATCH with completed: true
                        if self.auto_lock.get():
                            # Add delay to ensure pick is processed
                            sleep(0.3)
                            
                            self.log_message(f"🔒 Đang khóa {champion_name}...")
                            
                            try:
                                # Use the same endpoint with completed: true to lock
                                lock_data = {"championId": champion_id, "completed": True}
                                lock_response = self.request('patch', pick_url, '', lock_data)
                                
                                if lock_response.status_code == 204:
                                    self.log_message(f"🔒 Đã khóa {champion_name} thành công!")
                                else:
                                    self.log_message(f"⚠️ Không thể khóa {champion_name} - Status: {lock_response.status_code}")
                                        
                            except Exception as e:
                                self.log_message(f"⚠️ Lỗi kết nối khi khóa {champion_name}: {str(e)}")
                    else:
                        self.log_message(f"❌ Không thể chọn {champion_name} - Status: {r.status_code}")
                        if r.text:
                            self.log_message(f"🔍 Chi tiết lỗi chọn: {r.text}")
                        
        except Exception as e:
            self.log_message(f"❌ Lỗi khi chọn tướng: {str(e)}")
            
    def detect_league_path(self):
        """Detect League of Legends installation path from running LeagueClientUx.exe process"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if proc.info['name'] == 'LeagueClientUx.exe':
                        exe_path = proc.info['exe']
                        if exe_path:
                            # Extract the installation directory
                            league_dir = os.path.dirname(exe_path)
                            return league_dir
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            self.log_message(f"❌ Lỗi khi tìm kiếm League: {str(e)}")
        return None

    def wait_for_league(self):
        """Wait for League of Legends to start by detecting LeagueClientUx.exe process"""
        self.log_message("⏳ Đang chờ bạn vào trò chơi liên minh...")
        
        while self.is_running:
            # Try to detect League installation path
            league_dir = self.detect_league_path()
            
            if league_dir:
                lockpath = os.path.join(league_dir, 'lockfile')
                if os.path.isfile(lockpath):
                    try:
                        with open(lockpath, 'r') as f:
                            lockdata = f.read()
                        
                        lock = lockdata.split(':')
                        self.protocol = lock[4]
                        self.port = lock[2]
                        username = 'riot'
                        password = lock[3]
                        
                        # Setup session
                        userpass = b64encode(f'{username}:{password}'.encode()).decode('ascii')
                        self.headers = {'Authorization': f'Basic {userpass}'}
                        self.session = requests.session()
                        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                        
                        return True
                    except Exception as e:
                        self.log_message(f"❌ Lỗi khi đọc lockfile: {str(e)}")
                else:
                    self.log_message("⏳ Tìm thấy League Client nhưng chưa có lockfile, đang chờ...")
            
            sleep(2)
        return False
        
    def wait_for_login(self):
        """Wait for successful login"""
        while self.is_running:
            try:
                r = self.request('get', '/lol-login/v1/session')
                if r.status_code == 200:
                    session_data = r.json()
                    if session_data['state'] == 'SUCCEEDED':
                        self.summoner_id = session_data['summonerId']
                        return True
                    else:
                        self.log_message(f"⏳ Đang đăng nhập... ({session_data['state']})")
            except Exception:
                pass
            sleep(1)
        return False
        
    def request(self, method, path, query='', data=''):
        """Make API request to LCU"""
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
        
    def get_owned_champions(self):
        """Get list of owned champions - Updated for 2025"""
        try:
            # Try different API endpoints for champion data (2025 updated)
            endpoints = [
                '/lol-champions/v1/owned-champions-minimal',
                '/lol-champions/v1/inventories/1/champions-minimal', 
                '/lol-champions/v1/inventories/1/champions',
                '/lol-champions/v1/inventories/CHAMPION/champions',  # New endpoint for 2025
                '/lol-collections/v1/inventories/CHAMPION'  # Alternative 2025 endpoint
            ]
            
            self.owned_champions = []
            
            for endpoint in endpoints:
                try:
                    r = self.request('get', endpoint)
                    if r.status_code == 200:
                        owned = r.json()
                        if isinstance(owned, list):
                            # Extract champion IDs from different response formats
                            for champ in owned:
                                if isinstance(champ, dict):
                                    # Try different possible keys for champion ID
                                    champ_id = champ.get('id') or champ.get('championId') or champ.get('itemId')
                                    if champ_id and champ.get('active', True):
                                        self.owned_champions.append(champ_id)
                        elif isinstance(owned, dict) and 'champions' in owned:
                            # Handle nested response format
                            for champ in owned['champions']:
                                champ_id = champ.get('id') or champ.get('championId') or champ.get('itemId')
                                if champ_id and champ.get('active', True):
                                    self.owned_champions.append(champ_id)
                        
                        if self.owned_champions:
                            self.log_message(f"🎯 Bạn có {len(self.owned_champions)} tướng sở hữu")
                            break
                            
                except Exception as e:
                    self.log_message(f"⚠️ Lỗi khi thử endpoint {endpoint}: {str(e)}")
                    continue
            
            # Check selected champion ownership with improved logic
            if self.random_champion_names and len(self.random_champion_names) > 1:
                # Multiple champions selected for random - show combined message
                self.log_message(f"⏳ Đang chờ vào trận để pick random {len(self.random_champion_names)} tướng...")
            elif self.random_champion_names and len(self.random_champion_names) == 1:
                # Single champion - check ownership
                champion_name = self.random_champion_names[0]
                is_owned = self.check_champion_ownership_improved(champion_name)
                if not is_owned:
                    return False
                else:
                    self.log_message(f"⏳ Đang chờ vào trận để pick {champion_name}...")
            else:
                # Fallback to old logic for non-random selection
                selected = self.selected_champion.get()
                if selected and selected != "Random":
                    is_owned = self.check_champion_ownership_improved(selected)
                    if not is_owned:
                        return False
                    else:
                        self.log_message(f"⏳ Đang chờ vào trận để pick {selected}...")
                    
            return True
            
        except Exception as e:
            self.log_message(f"❌ Lỗi khi lấy danh sách tướng: {str(e)}")
            # Continue without ownership check but warn user
            self.log_message("⚠️ Sẽ thử pick trực tiếp mà không kiểm tra quyền sở hữu")
            self.owned_champions = []
            return True

    def check_champion_ownership_improved(self, champion_name):
        """Improved champion ownership checking for 2025"""
        try:
            # First try to find champion by name in all available champions
            correct_id = self.find_champion_id_by_name(champion_name)
            
            if correct_id:
                self.champion_ids[champion_name] = correct_id
                
                # Check if we own this champion
                if correct_id in self.owned_champions:
                    self.log_message(f"✅ Xác nhận có tướng {champion_name}")
                    return True
            
            # Fallback: Check primary ID and alternatives
            primary_id = self.champion_ids.get(champion_name)
            if primary_id and primary_id in self.owned_champions:
                self.log_message(f"✅ Xác nhận có tướng {champion_name}")
                return True
            
            # Check alternative IDs if available
            alt_ids = self.alternative_champion_ids.get(champion_name, [])
            for alt_id in alt_ids:
                if alt_id in self.owned_champions:
                    self.log_message(f"✅ Xác nhận có tướng {champion_name}")
                    self.champion_ids[champion_name] = alt_id
                    return True
            
            # Last resort: Try direct API call
            try:
                if primary_id:
                    r = self.request('get', f'/lol-champions/v1/champions/{primary_id}')
                    if r.status_code == 200:
                        champ_info = r.json()
                        if champ_info.get('ownership', {}).get('owned', False):
                            self.log_message(f"✅ API xác nhận có tướng {champion_name}")
                            return True
            except:
                pass
            
            # If no ownership found, show detailed debug info
            self.log_message(f"❌ Không tìm thấy tướng {champion_name} trong tài khoản!")
            self.log_message(f" Tổng số tướng sở hữu: {len(self.owned_champions)}")
            
            self.root.after(0, self.stop_auto_pick)
            return False
            
        except Exception as e:
            self.log_message(f"❌ Lỗi khi kiểm tra quyền sở hữu {champion_name}: {str(e)}")
            return False

    def find_champion_id_by_name(self, champion_name):
        """Find champion ID by searching through all available champions"""
        try:
            # Try different endpoints to get all champions
            endpoints = [
                '/lol-champions/v1/champions',
                '/lol-game-data/assets/v1/champions.json',
                '/lol-champions/v1/champions-minimal'
            ]
            
            for endpoint in endpoints:
                try:
                    r = self.request('get', endpoint)
                    if r.status_code == 200:
                        champions_data = r.json()
                        
                        if isinstance(champions_data, list):
                            for champ in champions_data:
                                if isinstance(champ, dict):
                                    champ_name = champ.get('name', '').lower()
                                    if champion_name.lower() in champ_name or champ_name in champion_name.lower():
                                        champ_id = champ.get('id') or champ.get('championId')
                                        if champ_id:
                                            return champ_id
                        elif isinstance(champions_data, dict):
                            # Handle nested data
                            for key, champ in champions_data.items():
                                if isinstance(champ, dict):
                                    champ_name = champ.get('name', '').lower()
                                    if champion_name.lower() in champ_name or champ_name in champion_name.lower():
                                        champ_id = champ.get('id') or champ.get('championId') or key
                                        if champ_id and str(champ_id).isdigit():
                                            return int(champ_id)
                                            
                except Exception:
                    continue
                    
            return None
            
        except Exception as e:
            self.log_message(f"⚠️ Lỗi khi tìm kiếm ID tướng: {str(e)}")
            return None

    def set_game_priority(self):
        """Set high priority for League of Legends process"""
        try:
            for p in psutil.process_iter():
                try:
                    if p.name() == 'League of Legends.exe':
                        p.nice(psutil.HIGH_PRIORITY_CLASS)
                        self.log_message("⚡ Đã thiết lập độ ưu tiên cao cho game")
                        break
                except (psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception:
            pass

    def open_champion_selection_dialog(self):
        """Open champion selection dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Chọn tướng cho Random")
        dialog.geometry("450x500")
        dialog.resizable(False, False)
        dialog.configure(bg='#203a43')
        
        # Remove window icon for dialog too
        try:
            dialog.iconbitmap('')
        except:
            pass
        
        # Center dialog
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Get available champions - all champions from the list
        available_champions = list(self.champion_ids.keys())
        available_champions.sort()  # Sort alphabetically for better user experience
        
        # Create champion variables first
        champion_vars = {}
        for champion in available_champions:
            var = tk.BooleanVar(value=champion in self.random_champion_names)
            champion_vars[champion] = var
        
        # Main frame
        main_frame = tk.Frame(dialog, bg='#203a43')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(main_frame, text="Chọn tướng cho chế độ Random", 
                             bg='#203a43', fg='#c9b037', font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 15))
        
        # Control buttons frame
        control_frame = tk.Frame(main_frame, bg='#203a43')
        control_frame.pack(fill='x', pady=(0, 10))
        
        select_all_btn = tk.Button(control_frame, text="Chọn tất cả",
                                 command=lambda: self.select_all_champions(champion_vars),
                                 font=('Arial', 10), bg='#27ae60', fg='white',
                                 activebackground='#2ecc71', relief='raised', bd=2)
        select_all_btn.pack(side='left')
        
        deselect_all_btn = tk.Button(control_frame, text="Bỏ chọn tất cả",
                                   command=lambda: self.deselect_all_champions(champion_vars),
                                   font=('Arial', 10), bg='#e74c3c', fg='white',
                                   activebackground='#c0392b', relief='raised', bd=2)
        deselect_all_btn.pack(side='left', padx=(10, 0))
        
        # Champions list frame with scrollbar
        list_frame = tk.Frame(main_frame, bg='#203a43')
        list_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        # Canvas and scrollbar for champions list
        canvas = tk.Canvas(list_frame, bg='#2c3e50', highlightthickness=0, height=120)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#2c3e50')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind('<Enter>', _bind_mousewheel)
        canvas.bind('<Leave>', _unbind_mousewheel)
        
        # Create champion checkboxes
        for i, champion in enumerate(available_champions):
            var = champion_vars[champion]
            
            cb = tk.Checkbutton(scrollable_frame, text=champion, variable=var,
                              bg='#2c3e50', fg='#ecf0f1', font=('Arial', 12),
                              activebackground='#34495e', selectcolor='#3498db',
                              anchor='w', padx=5)
            cb.pack(anchor='w', padx=10, pady=5, fill='x')
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Selection info
        info_frame = tk.Frame(main_frame, bg='#203a43')
        info_frame.pack(fill='x', pady=(0, 15))
        
        info_label = tk.Label(info_frame, text="💡 Chọn các tướng bạn muốn random. Nếu chọn quá 3 tướng, hệ thống sẽ hỏi xác nhận.",
                            bg='#203a43', fg='#f39c12', font=('Arial', 9), wraplength=350)
        info_label.pack()
        
        # Bottom buttons
        button_frame = tk.Frame(main_frame, bg='#203a43')
        button_frame.pack(fill='x', pady=(10, 0))
        
        # Cancel button on the left
        cancel_btn = tk.Button(button_frame, text="❌ HỦY",
                             command=dialog.destroy,
                             font=('Arial', 12), bg='#e74c3c', fg='white',
                             activebackground='#c0392b', relief='raised', bd=3, padx=20, pady=5)
        cancel_btn.pack(side='left')
        
        # Confirm button on the right - make it more prominent
        confirm_btn = tk.Button(button_frame, text="✅ XÁC NHẬN CHỌN",
                              command=lambda: self.confirm_champion_selection(dialog, champion_vars, available_champions),
                              font=('Arial', 12, 'bold'), bg='#27ae60', fg='white',
                              activebackground='#2ecc71', relief='raised', bd=4, padx=25, pady=8)
        confirm_btn.pack(side='right')
        
    def select_all_champions(self, champion_vars):
        """Select all champions in the dialog"""
        for var in champion_vars.values():
            var.set(True)
    
    def deselect_all_champions(self, champion_vars):
        """Deselect all champions in the dialog"""
        for var in champion_vars.values():
            var.set(False)
    
    def confirm_champion_selection(self, dialog, champion_vars, available_champions):
        """Confirm champion selection and update the display"""
        selected = [champion for champion, var in champion_vars.items() if var.get()]
        
        if not selected:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn ít nhất một tướng!")
            return
        
        # Close the selection dialog first
        dialog.destroy()
        
        # Handle single champion selection
        if len(selected) == 1:
            champion = selected[0]
            self.random_champion_names = selected
            self.update_champions_display()
            
            # Check ownership immediately for single champion
            if self.is_connected and self.session and self.headers:
                self.check_single_champion_ownership(champion)
            else:
                self.log_message(f"✅ Đã chọn tướng {champion}. Kết nối vào game để kiểm tra quyền sở hữu.")
        
        # Handle multiple champions selection
        else:
            self.random_champion_names = selected
            self.update_champions_display()
            
            if self.is_connected and self.session and self.headers:
                # Show loading and check all champions
                self.check_multiple_champions_ownership(selected)
            else:
                if len(selected) <= 3:
                    self.log_message(f"✅ Đã chọn {len(selected)} tướng: {', '.join(selected)}")
                else:
                    self.log_message(f"✅ Đã chọn {len(selected)} tướng random")
                self.log_message("🔗 Kết nối vào game để kiểm tra quyền sở hữu")
    
    def update_champions_display(self):
        """Update the champions display"""
        if not self.random_champion_names:
            self.champions_label.config(text="Chưa chọn tướng nào")
            return
        
        # Handle different display cases based on number of champions
        champion_count = len(self.random_champion_names)
        
        if champion_count == 1:
            display_text = f"Tướng đã chọn: {self.random_champion_names[0]}"
        elif champion_count <= 3:
            display_text = f"Random {champion_count} tướng: {', '.join(self.random_champion_names)}"
        else:
            first_three = ', '.join(self.random_champion_names[:3])
            remaining = champion_count - 3
            display_text = f"Random {champion_count} tướng: {first_three}... (+{remaining} tướng khác)"
        
        self.champions_label.config(text=display_text)
    
    def check_single_champion_ownership(self, champion_name):
        """Check ownership for single champion"""
        try:
            # Get owned champions first
            owned_champions = self.get_owned_champions_list()
            if not owned_champions:
                self.log_message(f"⚠️ Không thể kiểm tra tướng {champion_name}")
                return
                
            # Check ownership
            primary_id = self.champion_ids.get(champion_name)
            alt_ids = self.alternative_champion_ids.get(champion_name, [])
            all_ids_to_check = [primary_id] + alt_ids if primary_id else alt_ids
            
            champion_found = False
            for champ_id in all_ids_to_check:
                if champ_id and champ_id in owned_champions:
                    champion_found = True
                    break
                    
            if champion_found:
                self.log_message(f"✅ Xác nhận có tướng {champion_name}")
            else:
                self.log_message(f"❌ Bạn chưa có tướng {champion_name}")
                
        except Exception as e:
            self.log_message(f"⚠️ Lỗi khi kiểm tra tướng {champion_name}: {str(e)}")
    
    def check_multiple_champions_ownership(self, champions_list):
        """Check ownership for multiple champions with loading"""
        # Show loading
        self.loading_frame.pack(pady=(10, 0))
        
        # Start checking in background thread
        check_thread = threading.Thread(target=self._check_champions_thread, args=(champions_list,), daemon=True)
        check_thread.start()
    
    def _check_champions_thread(self, champions_list):
        """Background thread to check champions ownership"""
        try:
            # Get owned champions
            owned_champions = self.get_owned_champions_list()
            if not owned_champions:
                self.root.after(0, self._hide_loading)
                self.root.after(0, lambda: self.log_message("⚠️ Không thể kiểm tra tướng"))
                return
            
            # Check each champion
            missing_champions = []
            for champion_name in champions_list:
                primary_id = self.champion_ids.get(champion_name)
                alt_ids = self.alternative_champion_ids.get(champion_name, [])
                all_ids_to_check = [primary_id] + alt_ids if primary_id else alt_ids
                
                champion_found = False
                for champ_id in all_ids_to_check:
                    if champ_id and champ_id in owned_champions:
                        champion_found = True
                        break
                        
                if not champion_found:
                    missing_champions.append(champion_name)
            
            # Hide loading and show results
            self.root.after(0, self._hide_loading)
            
            if missing_champions:
                # Show missing champions dialog
                self.root.after(0, lambda: self._show_missing_champions_dialog(missing_champions))
            else:
                # All champions owned
                if len(champions_list) <= 3:
                    self.root.after(0, lambda: self.log_message(f"✅ Đã chọn random {len(champions_list)} tướng thành công: {', '.join(champions_list)}"))
                else:
                    self.root.after(0, lambda: self.log_message(f"✅ Đã chọn random {len(champions_list)} tướng thành công"))
                    
        except Exception as e:
            self.root.after(0, self._hide_loading)
            self.root.after(0, lambda: self.log_message(f"⚠️ Lỗi khi kiểm tra tướng: {str(e)}"))
    
    def _hide_loading(self):
        """Hide loading indicator"""
        self.loading_frame.pack_forget()
    
    def _show_missing_champions_dialog(self, missing_champions):
        """Show dialog for missing champions"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Tướng chưa sở hữu")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.configure(bg='#203a43')
        
        # Remove window icon
        try:
            dialog.iconbitmap('')
        except:
            pass
        
        # Center dialog
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Main frame
        main_frame = tk.Frame(dialog, bg='#203a43')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Warning icon and title
        title_frame = tk.Frame(main_frame, bg='#203a43')
        title_frame.pack(pady=(0, 15))
        
        title_label = tk.Label(title_frame, text="⚠️ Một số tướng chưa sở hữu", 
                             bg='#203a43', fg='#e74c3c', font=('Arial', 14, 'bold'))
        title_label.pack()
        
        # Message
        missing_text = ', '.join(missing_champions)
        message_text = f"Bạn chưa có tướng {missing_text} nên tôi sẽ tự động bỏ chọn tướng này nhé.\n\nHoặc bạn mua xong rồi tích vào lại rồi xác nhận lại nhé!"
        
        message_label = tk.Label(main_frame, text=message_text,
                               bg='#203a43', fg='#ffffff', font=('Arial', 11),
                               wraplength=350, justify='center')
        message_label.pack(pady=(0, 20))
        
        # Close button
        close_btn = tk.Button(main_frame, text="ĐÓNG",
                            command=lambda: self._close_missing_dialog(dialog, missing_champions),
                            font=('Arial', 12, 'bold'), bg='#3498db', fg='white',
                            activebackground='#2980b9', relief='raised', bd=3,
                            padx=30, pady=8)
        close_btn.pack()
    
    def _close_missing_dialog(self, dialog, missing_champions):
        """Close missing champions dialog and update selection"""
        dialog.destroy()
        
        # Remove missing champions from selection
        remaining_champions = [champ for champ in self.random_champion_names if champ not in missing_champions]
        self.random_champion_names = remaining_champions
        
        # Update display
        self.update_champions_display()
        
        # Log the update
        if remaining_champions:
            if len(remaining_champions) <= 3:
                self.log_message(f"✅ Đã cập nhật danh sách: {', '.join(remaining_champions)}")
            else:
                self.log_message(f"✅ Đã cập nhật danh sách còn {len(remaining_champions)} tướng")
        else:
            self.log_message("⚠️ Không còn tướng nào trong danh sách. Vui lòng chọn lại!")
    
    def get_owned_champions_list(self):
        """Get list of owned champion IDs"""
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
                        owned = r.json()
                        owned_champions = []
                        
                        if isinstance(owned, list):
                            for champ in owned:
                                if isinstance(champ, dict):
                                    champ_id = champ.get('id') or champ.get('championId') or champ.get('itemId')
                                    if champ_id and champ.get('active', True):
                                        owned_champions.append(champ_id)
                        elif isinstance(owned, dict) and 'champions' in owned:
                            for champ in owned['champions']:
                                champ_id = champ.get('id') or champ.get('championId') or champ.get('itemId')
                                if champ_id and champ.get('active', True):
                                    owned_champions.append(champ_id)
                        
                        if owned_champions:
                            return owned_champions
                except Exception:
                    continue
            
            return []
        except Exception:
            return []
    
    def get_random_champion_from_selected(self):
        """Get random champion from selected list"""
        if not self.random_champion_names:
            # Fallback to original behavior if no champions selected
            return self.get_random_champion()
        
        import random
        return random.choice(self.random_champion_names)


def main():
    root = tk.Tk()
    app = AutoPickLOLGUI(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        if app.is_running:
            app.stop_auto_pick()
        root.quit()


if __name__ == "__main__":
    main()
