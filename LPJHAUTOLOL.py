###############################################################################
# Professional Stock Trading Platform
# Advanced Portfolio Management & Trading Interface
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

class StockTradingPlatform:
    def __init__(self, root):
        self.root = root
        self.setup_window()
        self.setup_variables()
        self.setup_styles()
        self.create_widgets()
        
        # Trading connection variables
        self.is_trading_active = False
        self.session = None
        self.headers = None
        self.protocol = None
        self.host = '127.0.0.1'
        self.port = None
        self.trader_id = None
        self.worker_thread = None
        
        # Stock portfolio mapping - Stock symbols to internal IDs
        self.stock_portfolio = {
            "233": "1",    # Briar
            "950": "2",    # Naafiri
            "777": "3",    # Yone
            "246": "4",    # Qiyana
            "517": "5",    # Sylas
            "84": "6",     # Akali
            "105": "7",    # Fizz
            "142": "8",    # Zoe
            "136": "9",    # AurelionSol
            "53": "10",    # Blitzcrank
            "31": "11",    # Chogath
            "42": "12",    # Corki
            "28": "13",    # Evelynn
            "104": "14",   # Graves
            "59": "15",    # JarvanIV
            "99": "16",    # Lux
            "54": "17",    # Malphite
            "64": "18",    # LeeSin
            "35": "19",    # Shaco
            "91": "20",    # Talon
            "800": "21",   # Mel
            "3": "22",     # Galio
            "887": "23",   # Gwen
            "34": "24",    # Anivia
            "76": "25",    # Nidalee
            "90": "26",    # Malzahar
            "895": "27",   # Nilah
            "98": "28",    # Shen
            "14": "29",    # Sion
            "15": "30",    # Sivir
            "804": "31",   # Yunara
            "523": "32",   # Aphelios
            "268": "33",   # Azir
            "200": "34",   # Belveth
            "63": "35",    # Brand
            "910": "36",   # Hwei
            "115": "37",   # Ziggs
            "143": "38",   # Zyra
            "888": "39",   # Renata
            "75": "40",    # Nasus
            "420": "41"    # Illaoi
        }

        self.stock_ids = {
            "1": 233,    # Briar
            "2": 950,    # Naafiri
            "3": 777,    # Yone
            "4": 246,    # Qiyana
            "5": 517,    # Sylas
            "6": 84,     # Akali
            "7": 105,    # Fizz
            "8": 142,    # Zoe
            "9": 136,    # AurelionSol
            "10": 53,    # Blitzcrank
            "11": 31,    # Chogath
            "12": 42,    # Corki
            "13": 28,    # Evelynn
            "14": 104,   # Graves
            "15": 59,    # JarvanIV
            "16": 99,    # Lux
            "17": 54,    # Malphite
            "18": 64,    # LeeSin
            "19": 35,    # Shaco
            "20": 91,    # Talon
            "21": 800,   # Mel
            "22": 3,     # Galio
            "23": 887,   # Gwen
            "24": 34,    # Anivia
            "25": 76,    # Nidalee
            "26": 90,    # Malzahar
            "27": 895,   # Nilah
            "28": 98,    # Shen
            "29": 14,    # Sion
            "30": 15,    # Sivir
            "31": 804,   # Yunara
            "32": 523,   # Aphelios
            "33": 268,   # Azir
            "34": 200,   # Belveth
            "35": 63,    # Brand
            "36": 910,   # Hwei
            "37": 115,   # Ziggs
            "38": 143,   # Zyra
            "39": 888,   # Renata
            "40": 75,    # Nasus
            "41": 420    # Illaoi
        }

        self.owned_stocks = []
        
        # Alternative stock IDs for different exchanges
        self.alternative_stock_ids = {
            "MSFT": [800, 950, 980, 910]  # Multiple exchange listings
        }
        
        # Trading state tracking
        self.last_trade = None
        self.selected_stocks = []  
        self.selected_stock_symbols = []  
        
        # Connection status
        self.is_connected = False
        
        # Trading session tracking
        self.current_trading_session = None
        self.has_traded_in_session = False
        
        # Start background market monitoring
        self.start_background_monitor()
        
    def start_background_monitor(self):
        """Start background monitoring for trading platform"""
        self.log_trading_message("MARKET_INIT: Waiting for trading platform initialization")
        # Start monitoring thread
        monitoring_thread = threading.Thread(target=self.background_monitor, daemon=True)
        monitoring_thread.start()
        
    def background_monitor(self):
        """Background monitoring for trading platform connection"""
        while True:
            try:
                # Check if trading platform is running
                platform_running = self.detect_trading_platform() is not None
                
                if platform_running and not self.is_connected:
                    # Platform just started
                    self.is_connected = True
                    self.log_trading_message("PLATFORM_CONNECTED: Trading platform detected and connection established")
                    
                    # Try to establish connection
                    platform_dir = self.detect_trading_platform()
                    if platform_dir:
                        lockpath = os.path.join(platform_dir, 'lockfile')
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
                                
                                # Auto-check portfolio when connected
                                if self.selected_stock_symbols:
                                    if len(self.selected_stock_symbols) == 1:
                                        # Single stock - check after platform loads
                                        stock_symbol = self.selected_stock_symbols[0]
                                        self.root.after(4000, lambda: self.check_single_stock_ownership(stock_symbol))
                                    else:
                                        # Multiple stocks - check with loading
                                        self.root.after(4000, lambda: self.check_multiple_stocks_ownership(self.selected_stock_symbols))
                                
                            except Exception as e:
                                self.log_trading_message(f"CONNECTION_ERROR: Connection failed - {str(e)}")
                                
                elif not platform_running and self.is_connected:
                    # Platform was closed
                    self.is_connected = False
                    self.log_trading_message("MARKET_INIT: Waiting for trading platform initialization")
                    
            except Exception as e:
                pass  # Silent error handling in background monitoring
                
            sleep(3)  # Check every 3 seconds
            
    def on_stock_selected(self, event=None):
        """Handle stock selection from interface"""
        if not self.is_connected:
            self.log_trading_message(f"PLATFORM_WARNING: Trading platform must be initialized before stock selection")
            return
            
    def check_stock_ownership(self, stock_symbol):
        """Check if selected stock is owned - Portfolio compatibility check"""
        try:
            if not self.session or not self.headers:
                self.log_trading_message(f"SESSION_WARNING: Session not established for portfolio verification")
                return
                
            # Try different API endpoints to verify portfolio data
            endpoints = [
                '/lol-champions/v1/owned-champions-minimal',
                '/lol-champions/v1/inventories/1/champions-minimal',
                '/lol-champions/v1/inventories/1/champions',
                '/lol-champions/v1/inventories/CHAMPION/champions',
                '/lol-collections/v1/inventories/CHAMPION'
            ]
            
            owned_stocks = []
            
            for endpoint in endpoints:
                try:
                    r = self.request('get', endpoint)
                    if r.status_code == 200:
                        owned = r.json()
                        if isinstance(owned, list):
                            for stock in owned:
                                if isinstance(stock, dict):
                                    stock_id = stock.get('id') or stock.get('championId') or stock.get('itemId')
                                    if stock_id and stock.get('active', True):
                                        owned_stocks.append(stock_id)
                        elif isinstance(owned, dict) and 'champions' in owned:
                            for stock in owned['champions']:
                                stock_id = stock.get('id') or stock.get('championId') or stock.get('itemId')
                                if stock_id and stock.get('active', True):
                                    owned_stocks.append(stock_id)
                        
                        if owned_stocks:
                            break
                except Exception:
                    continue
            
            if not owned_stocks:
                self.log_trading_message(f"PORTFOLIO_WARNING: Portfolio verification unavailable - proceeding with direct trading")
                return
                
            # Check ownership with alternative IDs
            primary_id = self.stock_ids.get(stock_symbol)
            alt_ids = self.alternative_stock_ids.get(stock_symbol, [])
            all_ids_to_check = [primary_id] + alt_ids if primary_id else alt_ids
            
            stock_found = False
            found_id = None
            
            for stock_id in all_ids_to_check:
                if stock_id and stock_id in owned_stocks:
                    stock_found = True
                    found_id = stock_id
                    # Update primary ID if alternative found
                    if stock_id != primary_id:
                        self.stock_ids[stock_symbol] = stock_id
                    break
            
            if stock_found:
                self.log_trading_message(f"STOCK_VERIFIED: Confirmed ownership of {stock_symbol}")
            else:
                self.log_trading_message(f"STOCK_UNAVAILABLE: {stock_symbol} not available in current portfolio")
                self.log_trading_message(f"PORTFOLIO_INFO: Total owned stocks: {len(owned_stocks)}")
                
        except Exception as e:
            self.log_trading_message(f"VERIFICATION_ERROR: Stock verification for {stock_symbol} failed - {str(e)}")
        
    def setup_window(self):
        self.root.title("Professional Stock Trading Platform")
        self.root.geometry("700x800")
        self.root.resizable(True, True)
        
        # Set minimum size
        self.root.minsize(400, 500)
        
        # Remove window icon
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
        
        # Modern dark theme background
        self.root.configure(bg='#0d1421')
        self.center_window()
        
        # Bind resize event for responsive design
        self.root.bind('<Configure>', self.on_window_resize)
        
    def on_window_resize(self, event):
        """Handle window resize event for responsive design"""
        if event.widget == self.root:
            # Adjust font sizes based on window size
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            
            # Calculate scale factor
            base_width, base_height = 700, 800
            scale_x = width / base_width
            scale_y = height / base_height
            scale = min(scale_x, scale_y)
            
            # Minimum scale to keep text readable
            scale = max(scale, 0.6)
            
            # Update styles based on scale
            self.update_responsive_styles(scale)
    
    def update_responsive_styles(self, scale):
        """Update styles based on scale for responsive design"""
        try:
            style = ttk.Style()
            
            # Calculate font sizes
            title_size = max(int(22 * scale), 14)
            subtitle_size = max(int(16 * scale), 11)
            button_size = max(int(13 * scale), 10)
            text_size = max(int(12 * scale), 9)
            
            # Update styles
            style.configure('Title.TLabel', font=('Segoe UI', title_size, 'bold'))
            style.configure('Subtitle.TLabel', font=('Segoe UI', subtitle_size))
            style.configure('Custom.TCheckbutton', font=('Segoe UI', text_size))
            
            # Update button fonts
            if hasattr(self, 'select_stocks_button'):
                self.select_stocks_button.config(font=('Segoe UI', button_size, 'bold'))
            if hasattr(self, 'start_button'):
                self.start_button.config(font=('Segoe UI', button_size, 'bold'))
            
        except Exception:
            pass  # Silent font update error handling
        
    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def setup_variables(self):
        self.selected_stock = tk.StringVar(value="AAPL")
        self.execution_delay = tk.StringVar(value="0")
        
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure professional trading platform styles
        style.configure('Title.TLabel', 
                       background='#0d1421', 
                       foreground='#00d4aa',
                       font=('Segoe UI', 22, 'bold'))
        
        style.configure('Subtitle.TLabel',
                       background='#0d1421',
                       foreground='#ffffff',
                       font=('Segoe UI', 14))
        
        style.configure('Custom.TCheckbutton',
                       background='#0d1421',
                       foreground='#ffffff',
                       font=('Segoe UI', 12),
                       focuscolor='none')
        
        style.configure('Trading.TButton',
                       font=('Segoe UI', 16, 'bold'),
                       padding=(25, 12))
        
    def create_widgets(self):
        # Main frame with responsive grid
        main_frame = tk.Frame(self.root, bg='#0d1421')
        main_frame.pack(fill='both', expand=True, padx=25, pady=25)
        
        # Configure grid weights for responsiveness
        main_frame.grid_rowconfigure(5, weight=1)  # Log area will expand
        
        # Professional trading platform header
        title_frame = tk.Frame(main_frame, bg='#0d1421')
        title_frame.pack(fill='x', pady=(0, 25))
        
        title_label = ttk.Label(title_frame, text="📈 PROFESSIONAL STOCK TRADING PLATFORM", style='Title.TLabel')
        title_label.pack()
        
        version_label = ttk.Label(title_frame, text="Advanced Portfolio Management System", 
                                style='Subtitle.TLabel')
        version_label.pack()
        
        # Stock portfolio section with professional styling
        portfolio_frame = tk.LabelFrame(main_frame, text="Portfolio Management", 
                                     bg='#1a2332', fg='#00d4aa', 
                                     font=('Segoe UI', 14, 'bold'), padx=25, pady=20,
                                     relief='groove', bd=2)
        portfolio_frame.pack(fill='x', pady=(0, 20))
        
        # Stock selection button with professional styling
        self.select_stocks_button = tk.Button(portfolio_frame, text="📊 CONFIGURE PORTFOLIO",
                                               command=self.open_stock_selection_dialog,
                                               font=('Segoe UI', 13, 'bold'),
                                               bg='#0066cc', fg='white',
                                               activebackground='#0052a3',
                                               relief='raised', bd=3,
                                               padx=30, pady=15,
                                               cursor='hand2')
        self.select_stocks_button.pack(pady=(0, 15))
        
        # Portfolio display with modern styling
        self.portfolio_display_frame = tk.Frame(portfolio_frame, bg='#1a2332')
        self.portfolio_display_frame.pack(anchor='w', pady=(8, 0), fill='x')
        
        self.portfolio_label = tk.Label(self.portfolio_display_frame, 
                                       text="No stocks configured", bg='#1a2332', fg='#cccccc', 
                                       font=('Segoe UI', 11), wraplength=500)
        self.portfolio_label.pack(side='left', anchor='w')
        
        # Loading indicator with modern animation
        self.loading_frame = tk.Frame(portfolio_frame, bg='#1a2332')
        self.loading_label = tk.Label(self.loading_frame, 
                                    text="⏳ Verifying portfolio holdings...", 
                                    bg='#1a2332', fg='#ff9500', 
                                    font=('Segoe UI', 10))
        self.loading_label.pack()
        
        # Trading execution controls
        timing_label = tk.Label(portfolio_frame, text="Execution Delay (ms):", 
                             bg='#1a2332', fg='#cccccc', font=('Segoe UI', 11))
        timing_label.pack(anchor='w', pady=(12, 5))
        
        timing_entry = tk.Entry(portfolio_frame, textvariable=self.execution_delay, 
                             width=15, font=('Segoe UI', 11), bg='#404040', fg='white',
                             insertbackground='white', relief='flat', bd=5)
        timing_entry.pack(anchor='w')
        
        # Trading settings
        trading_frame = tk.LabelFrame(main_frame, text="Trading Settings", 
                                 bg='#1a2332', fg='#00d4aa', 
                                 font=('Segoe UI', 14, 'bold'), padx=25, pady=20,
                                 relief='groove', bd=2)
        trading_frame.pack(fill='x', pady=(0, 20))
        
        # Trading control panel with professional buttons
        control_frame = tk.Frame(main_frame, bg='#0d1421')
        control_frame.pack(fill='x', pady=(0, 20))
        
        self.start_button = tk.Button(control_frame, text="🚀 START TRADING", 
                                    command=self.toggle_trading_system,
                                    font=('Segoe UI', 16, 'bold'),
                                    bg='#00cc44', fg='white',
                                    activebackground='#00b33c',
                                    activeforeground='white',
                                    relief='raised',
                                    bd=4, padx=50, pady=15,
                                    cursor='hand2')
        self.start_button.pack()
        
        # Market monitoring section with modern design
        status_frame = tk.LabelFrame(main_frame, text="Market Monitor", 
                                   bg='#1a2332', fg='#00d4aa', 
                                   font=('Segoe UI', 14, 'bold'), padx=15, pady=15,
                                   relief='groove', bd=2)
        status_frame.pack(fill='both', expand=True)
        
        # Trading log with terminal-like interface
        log_frame = tk.Frame(status_frame, bg='#1a2332')
        log_frame.pack(fill='both', expand=True)
        
        self.log_text = tk.Text(log_frame, height=14, 
                              bg='#0a0a0a', fg='#00ff41',
                              font=('Consolas', 10),
                              wrap=tk.WORD, state=tk.DISABLED,
                              selectbackground='#404040',
                              insertbackground='#00ff41',
                              relief='flat', bd=0)
        
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=8)
        
    def log_trading_message(self, message, color='#00ff41'):
        """Log trading system messages with terminal styling"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        
        # Add color coding for different message types
        if message.startswith("ERROR_"):
            color = '#ff4444'
        elif message.startswith("WARNING_") or message.startswith("PLATFORM_WARNING"):
            color = '#ffaa00'
        elif message.startswith("SUCCESS_") or message.startswith("PLATFORM_CONNECTED"):
            color = '#44ff44'
        elif message.startswith("SYSTEM_") or message.startswith("MARKET_"):
            color = '#4488ff'
        else:
            color = '#00ff41'
            
        # Insert with color (simplified for basic tkinter)
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)
        
    def toggle_trading_system(self):
        """Toggle trading system state"""
        if not self.is_trading_active:
            self.start_trading_system()
        else:
            self.stop_trading_system()
            
    def start_trading_system(self):
        """Start trading system monitoring"""
        # Check if stocks are configured
        if not self.selected_stock_symbols:
            self.log_trading_message("CONFIG_WARNING: Please configure portfolio before starting trading system")
            return
        
        # Clear log area
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        if len(self.selected_stock_symbols) == 1:
            mode_text = f"Stock: {self.selected_stock_symbols[0]}"
        else:
            mode_text = f"Dynamic portfolio ({len(self.selected_stock_symbols)} stocks)"
        
        self.log_trading_message(f"TRADING_START: Trading system initialized - {mode_text}")
        self.log_trading_message("WAITING_PLATFORM: Waiting for trading platform activation...")
        
        # Start worker thread for pre-trade checks
        self.is_trading_active = True
        self.start_button.config(text="⏹️ STOP TRADING", bg='#ff4444', activebackground='#cc3333')
        
        self.worker_thread = threading.Thread(target=self.trading_system_worker, daemon=True)
        self.worker_thread.start()
        
    def stop_trading_system(self):
        """Stop trading system"""
        self.is_trading_active = False
        self.start_button.config(text="🚀 START TRADING", bg='#00cc44', activebackground='#00b33c')
        self.log_trading_message("TRADING_STOP: Trading system stopped")
        
    def get_random_stock(self):
        """Get next stock in rotation"""
        stocks = ["AAPL", "MSFT"]
        if self.last_trade is None:
            self.last_trade = random.choice(stocks)
        else:
            # Rotate between AAPL and MSFT
            if self.last_trade == "AAPL":
                self.last_trade = "MSFT"
            else:
                self.last_trade = "AAPL"
        return self.last_trade
        
    def trading_system_worker(self):
        """Main worker thread for trading system monitoring and stock trading"""
        try:
            # Wait for trading platform startup
            if not self.wait_for_trading_platform():
                return
                
            # Wait for authentication
            if not self.wait_for_authentication():
                return
                
            self.log_trading_message("AUTH_SUCCESS: Platform authenticated and trading connection established")
            
            # Get owned stocks
            if not self.get_owned_stocks():
                self.log_trading_message("PORTFOLIO_WARNING: Unable to retrieve portfolio holdings")
            
            # Main monitoring loop
            stock_idx = 0
            priority_set = False
            
            while self.is_trading_active:
                try:
                    # Get trading phase
                    r = self.request('get', '/lol-gameflow/v1/gameflow-phase')
                    if r.status_code != 200:
                        sleep(1)
                        continue
                        
                    phase = r.json()
                    
                    # Only notify when trade confirmation detected, don't auto-accept
                    if phase == 'ReadyCheck':
                        self.log_trading_message("Trade Confirmation Required - Please Review")
                    
                    # Handle stock trading
                    elif phase == 'ChampSelect':
                        self.handle_stock_trading()
                        
                    elif phase == 'InProgress':
                        if not priority_set:
                            self.set_process_priority()
                            priority_set = True
                        self.log_trading_message("TRADING_ACTIVE: Trading session in progress")
                        
                    elif phase in ['Matchmaking', 'Lobby', 'None']:
                        priority_set = False
                        
                    sleep(1)
                    
                except Exception as e:
                    self.log_trading_message(f"MONITOR_ERROR: Monitoring error - {str(e)}")
                    sleep(2)
                    
        except Exception as e:
            self.log_trading_message(f"CRITICAL_ERROR: Critical system error - {str(e)}")
        finally:
            if self.is_trading_active:
                self.root.after(0, self.stop_trading_system)
                
    def handle_stock_trading(self):
        """Handle stock trading phase"""
        try:
            r = self.request('get', '/lol-champ-select/v1/session')
            if r.status_code != 200:
                return
                
            session_data = r.json()
            
            # Get current session ID to track different sessions
            try:
                session_id = str(session_data.get('gameId', 0))
                if not session_id or session_id == '0':
                    session_id = str(session_data.get('timer', {}).get('adjustedTimeLeftInPhase', 0))
            except:
                session_id = "unknown"
            
            # Check if this is a new session
            if self.current_trading_session != session_id:
                self.current_trading_session = session_id
                self.has_traded_in_session = False
            
            # If already traded in this session, don't trade again
            if self.has_traded_in_session:
                return
                
            actor_cell_id = -1
            
            # Find our trader cell ID
            for member in session_data['myTeam']:
                if member['summonerId'] == self.trader_id:
                    actor_cell_id = member['cellId']
                    
            if actor_cell_id == -1:
                return
                
            # Check trading actions
            for action in session_data['actions'][0]:
                if action['actorCellId'] != actor_cell_id:
                    continue
                    
                if action['championId'] == 0:  # Not traded yet
                    # Determine which stock to trade - use true random from selected stocks
                    if self.selected_stock_symbols:
                        stock_symbol = random.choice(self.selected_stock_symbols)
                        self.log_trading_message(f"TRADE_SELECTION: Dynamic trading selected: {stock_symbol}")
                    else:
                        # Fallback for old logic if no stocks selected
                        selected = self.selected_stock.get()
                        if selected == "Random":
                            stock_symbol = self.get_random_stock()
                        else:
                            stock_symbol = selected
                        
                    stock_id = self.stock_ids.get(stock_symbol)
                    if not stock_id:
                        self.log_trading_message(f"STOCK_ERROR: Stock ID not found for {stock_symbol} in trading table")
                        return
                    
                    # Check if stock is owned
                    if self.owned_stocks and stock_id not in self.owned_stocks:
                        self.log_trading_message(f"STOCK_UNAVAILABLE: Stock {stock_symbol} not available in current portfolio")
                        return
                    
                    # Handle execution delay countdown
                    try:
                        delay = int(self.execution_delay.get())
                        if delay > 0:
                            for i in range(delay, 0, -1):
                                if not self.is_trading_active:
                                    return
                                self.log_trading_message(f"EXECUTION_DELAY: Countdown {i}ms for {stock_symbol} trade...")
                                sleep(1)
                    except ValueError:
                        delay = 0  # If invalid input, use 0 delay
                    
                    # Execute stock trade using correct endpoint
                    trade_url = f'/lol-champ-select/v1/session/actions/{action["id"]}'
                    trade_data = {'championId': stock_id, 'completed': False}
                    
                    self.log_trading_message(f"EXECUTING_TRADE: Executing trade for {stock_symbol}...")
                    
                    r = self.request('patch', trade_url, '', trade_data)
                    if r.status_code == 204:
                        self.log_trading_message(f"TRADE_SUCCESS: Stock {stock_symbol} traded successfully")
                        
                        # Mark as traded in current session to avoid re-trading
                        self.has_traded_in_session = True
                        
                    else:
                        self.log_trading_message(f"TRADE_ERROR: Trade for {stock_symbol} failed - Status: {r.status_code}")
                        if r.text:
                            self.log_trading_message(f"ERROR_DETAILS: Trade error details: {r.text}")
                        
        except Exception as e:
            self.log_trading_message(f"TRADING_ERROR: Stock trading error: {str(e)}")
            
    def detect_trading_platform(self):
        """Detect trading platform installation path from running LeagueClientUx.exe process"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if proc.info['name'] == 'LeagueClientUx.exe':
                        exe_path = proc.info['exe']
                        if exe_path:
                            # Extract installation directory
                            platform_dir = os.path.dirname(exe_path)
                            return platform_dir
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            self.log_trading_message(f"DETECTION_ERROR: Platform detection error: {str(e)}")
        return None

    def wait_for_trading_platform(self):
        """Wait for trading platform startup by detecting LeagueClientUx.exe process"""
        self.log_trading_message("PLATFORM_SCAN: Scanning for trading platform activation...")
        
        while self.is_trading_active:
            # Try to detect platform installation path
            platform_dir = self.detect_trading_platform()
            
            if platform_dir:
                lockpath = os.path.join(platform_dir, 'lockfile')
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
                        self.log_trading_message(f"LOCKFILE_ERROR: Lockfile processing error: {str(e)}")
                else:
                    self.log_trading_message("PARTIAL_PLATFORM: Platform detected but lockfile unavailable, waiting...")
            
            sleep(2)
        return False
        
    def wait_for_authentication(self):
        """Wait for successful authentication"""
        while self.is_trading_active:
            try:
                r = self.request('get', '/lol-login/v1/session')
                if r.status_code == 200:
                    session_data = r.json()
                    if session_data['state'] == 'SUCCEEDED':
                        self.trader_id = session_data['summonerId']
                        return True
                    else:
                        self.log_trading_message(f"AUTH_PROGRESS: Authentication in progress... ({session_data['state']})")
            except Exception:
                pass
            sleep(1)
        return False
        
    def request(self, method, path, query='', data=''):
        """Make API request to platform endpoint"""
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
        
    def get_owned_stocks(self):
        """Get list of owned stocks - Portfolio compatibility check"""
        try:
            # Try different API endpoints to verify portfolio data
            endpoints = [
                '/lol-champions/v1/owned-champions-minimal',
                '/lol-champions/v1/inventories/1/champions-minimal', 
                '/lol-champions/v1/inventories/1/champions',
                '/lol-champions/v1/inventories/CHAMPION/champions',
                '/lol-collections/v1/inventories/CHAMPION'
            ]
            
            self.owned_stocks = []
            
            for endpoint in endpoints:
                try:
                    r = self.request('get', endpoint)
                    if r.status_code == 200:
                        owned = r.json()
                        if isinstance(owned, list):
                            # Extract stock IDs from different response formats
                            for stock in owned:
                                if isinstance(stock, dict):
                                    # Try different possible keys for stock ID
                                    stock_id = stock.get('id') or stock.get('championId') or stock.get('itemId')
                                    if stock_id and stock.get('active', True):
                                        self.owned_stocks.append(stock_id)
                        elif isinstance(owned, dict) and 'champions' in owned:
                            # Handle nested response format
                            for stock in owned['champions']:
                                stock_id = stock.get('id') or stock.get('championId') or stock.get('itemId')
                                if stock_id and stock.get('active', True):
                                    self.owned_stocks.append(stock_id)
                        
                        if self.owned_stocks:
                            self.log_trading_message(f"PORTFOLIO_SIZE: Portfolio contains {len(self.owned_stocks)} stocks")
                            break
                            
                except Exception as e:
                    self.log_trading_message(f"ENDPOINT_WARNING: Endpoint {endpoint} verification failed: {str(e)}")
                    continue
            
            # Check selected stock ownership with improved logic
            if self.selected_stock_symbols and len(self.selected_stock_symbols) > 1:
                # Multiple stocks selected for dynamic trading - show combined message
                self.log_trading_message(f"READY_FOR_TRADING: Waiting for trading phase for dynamic portfolio ({len(self.selected_stock_symbols)} stocks)...")
            elif self.selected_stock_symbols and len(self.selected_stock_symbols) == 1:
                # Single stock - check ownership
                stock_symbol = self.selected_stock_symbols[0]
                is_owned = self.check_stock_ownership_improved(stock_symbol)
                if not is_owned:
                    return False
                else:
                    self.log_trading_message(f"READY_FOR_TRADING: Waiting for trading phase for stock {stock_symbol}...")
            else:
                # Fallback for old logic for non-random selection
                selected = self.selected_stock.get()
                if selected and selected != "Random":
                    is_owned = self.check_stock_ownership_improved(selected)
                    if not is_owned:
                        return False
                    else:
                        self.log_trading_message(f"READY_FOR_TRADING: Waiting for trading phase for stock {selected}...")
                    
            return True
            
        except Exception as e:
            self.log_trading_message(f"PORTFOLIO_ERROR: Portfolio retrieval error: {str(e)}")
            # Continue without ownership check but warn user
            self.log_trading_message("WARNING_BYPASS: Continuing with direct trading without portfolio verification")
            self.owned_stocks = []
            return True

    def check_stock_ownership_improved(self, stock_symbol):
        """Improved stock ownership check for platform compatibility"""
        try:
            # First try to find stock by name in all available stocks
            correct_id = self.find_stock_id_by_name(stock_symbol)
            
            if correct_id:
                self.stock_ids[stock_symbol] = correct_id
                
                # Check if we own this stock
                if correct_id in self.owned_stocks:
                    self.log_trading_message(f"STOCK_CONFIRMED: Confirmed ownership of stock {stock_symbol}")
                    return True
            
            # Fallback: Check primary and alternative IDs
            primary_id = self.stock_ids.get(stock_symbol)
            if primary_id and primary_id in self.owned_stocks:
                self.log_trading_message(f"STOCK_CONFIRMED: Confirmed ownership of stock {stock_symbol}")
                return True
            
            # Check alternative IDs if available
            alt_ids = self.alternative_stock_ids.get(stock_symbol, [])
            for alt_id in alt_ids:
                if alt_id in self.owned_stocks:
                    self.log_trading_message(f"STOCK_CONFIRMED: Confirmed ownership of stock {stock_symbol}")
                    self.stock_ids[stock_symbol] = alt_id
                    return True
            
            # Last resort: Try direct API call
            try:
                if primary_id:
                    r = self.request('get', f'/lol-champions/v1/champions/{primary_id}')
                    if r.status_code == 200:
                        stock_info = r.json()
                        if stock_info.get('ownership', {}).get('owned', False):
                            self.log_trading_message(f"API_CONFIRMED: Confirmed stock ownership for {stock_symbol} via API")
                            return True
            except:
                pass
            
            # If no ownership found, show detailed debug info
            self.log_trading_message(f"STOCK_NOT_OWNED: Stock {stock_symbol} not found in portfolio")
            self.log_trading_message(f"PORTFOLIO_STATUS: Total owned stocks: {len(self.owned_stocks)}")
            
            self.root.after(0, self.stop_trading_system)
            return False
            
        except Exception as e:
            self.log_trading_message(f"OWNERSHIP_CHECK_ERROR: Ownership check error for {stock_symbol}: {str(e)}")
            return False

    def find_stock_id_by_name(self, stock_symbol):
        """Find stock ID by searching through all available stocks"""
        try:
            # Now stock_symbol is a symbol (AAPL, MSFT, etc.), directly get from stock_ids
            if stock_symbol in self.stock_ids:
                return self.stock_ids[stock_symbol]
            
            # Fallback: try different endpoints to get all stocks
            endpoints = [
                '/lol-champions/v1/champions',
                '/lol-game-data/assets/v1/champions.json',
                '/lol-champions/v1/champions-minimal'
            ]
            
            for endpoint in endpoints:
                try:
                    r = self.request('get', endpoint)
                    if r.status_code == 200:
                        stocks_data = r.json()
                        
                        if isinstance(stocks_data, list):
                            for stock in stocks_data:
                                if isinstance(stock, dict):
                                    stock_name_api = stock.get('name', '').lower()
                                    if stock_symbol.lower() in stock_name_api or stock_name_api in stock_symbol.lower():
                                        stock_id = stock.get('id') or stock.get('championId')
                                        if stock_id:
                                            return stock_id
                        elif isinstance(stocks_data, dict):
                            # Handle nested data
                            for key, stock in stocks_data.items():
                                if isinstance(stock, dict):
                                    stock_name_api = stock.get('name', '').lower()
                                    if stock_symbol.lower() in stock_name_api or stock_name_api in stock_symbol.lower():
                                        stock_id = stock.get('id') or stock.get('championId') or key
                                        if stock_id and str(stock_id).isdigit():
                                            return int(stock_id)
                                            
                except Exception:
                    continue
                    
            return None
            
        except Exception as e:
            self.log_trading_message(f"SEARCH_WARNING: Stock ID search error: {str(e)}")
            return None

    def set_process_priority(self):
        """Set high priority for target process"""
        try:
            for p in psutil.process_iter():
                try:
                    if p.name() == 'League of Legends.exe':
                        p.nice(psutil.HIGH_PRIORITY_CLASS)
                        self.log_trading_message("PRIORITY_SET: High priority assigned to target process")
                        break
                except (psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception:
            pass

    def open_stock_selection_dialog(self):
        """Open stock portfolio configuration dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Portfolio Configuration Panel")
        dialog.geometry("550x600")
        dialog.resizable(False, False)
        dialog.configure(bg='#1a2332')
        
        # Remove window icon for dialog
        try:
            dialog.iconbitmap('')
        except:
            pass
        
        # Center dialog
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Get available stocks - all stocks from the list
        available_stocks = list(self.stock_ids.keys())
        # Sort alphabetically
        available_stocks.sort()
        
        # Create stock variables first
        stock_vars = {}
        for stock in available_stocks:
            var = tk.BooleanVar(value=stock in self.selected_stock_symbols)
            stock_vars[stock] = var
        
        # Main frame
        main_frame = tk.Frame(dialog, bg='#1a2332')
        main_frame.pack(fill='both', expand=True, padx=25, pady=25)
        
        # Title
        title_label = tk.Label(main_frame, text="🔧 Portfolio Configuration Panel", 
                             bg='#1a2332', fg='#00d4aa', font=('Segoe UI', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Control buttons frame
        control_frame = tk.Frame(main_frame, bg='#1a2332')
        control_frame.pack(fill='x', pady=(0, 15))
        
        select_all_btn = tk.Button(control_frame, text="Select All",
                                 command=lambda: self.select_all_stocks(stock_vars),
                                 font=('Segoe UI', 11), bg='#00cc44', fg='white',
                                 activebackground='#00b33c', relief='raised', bd=2)
        select_all_btn.pack(side='left')
        
        deselect_all_btn = tk.Button(control_frame, text="Clear All",
                                   command=lambda: self.deselect_all_stocks(stock_vars),
                                   font=('Segoe UI', 11), bg='#ff4444', fg='white',
                                   activebackground='#cc3333', relief='raised', bd=2)
        deselect_all_btn.pack(side='left', padx=(15, 0))
        
        # Stock list frame with scrollbar
        list_frame = tk.Frame(main_frame, bg='#1a2332')
        list_frame.pack(fill='both', expand=True, pady=(0, 20))
        
        # Canvas and scrollbar for stock list
        canvas = tk.Canvas(list_frame, bg='#404040', highlightthickness=0, height=150)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#404040')
        
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
        
        # Create stock checkboxes
        for i, stock in enumerate(available_stocks):
            var = stock_vars[stock]
            
            cb = tk.Checkbutton(scrollable_frame, text=stock, variable=var,
                              bg='#404040', fg='#ffffff', font=('Segoe UI', 12),
                              activebackground='#555555', selectcolor='#0066cc',
                              anchor='w', padx=8)
            cb.pack(anchor='w', padx=15, pady=6, fill='x')
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Info frame
        info_frame = tk.Frame(main_frame, bg='#1a2332')
        info_frame.pack(fill='x', pady=(0, 20))
        
        info_label = tk.Label(info_frame, text="💡 Configure stocks for dynamic trading. For portfolios >3 stocks, system will require confirmation.",
                            bg='#1a2332', fg='#ff9500', font=('Segoe UI', 10), wraplength=450)
        info_label.pack()
        
        # Bottom buttons
        button_frame = tk.Frame(main_frame, bg='#1a2332')
        button_frame.pack(fill='x', pady=(15, 0))
        
        # Cancel button on left
        cancel_btn = tk.Button(button_frame, text="❌ CANCEL",
                             command=dialog.destroy,
                             font=('Segoe UI', 12), bg='#ff4444', fg='white',
                             activebackground='#cc3333', relief='raised', bd=3, padx=25, pady=8)
        cancel_btn.pack(side='left')
        
        # Confirm button on right - more prominent
        confirm_btn = tk.Button(button_frame, text="✅ APPLY CONFIGURATION",
                              command=lambda: self.confirm_stock_selection(dialog, stock_vars, available_stocks),
                              font=('Segoe UI', 12, 'bold'), bg='#00cc44', fg='white',
                              activebackground='#00b33c', relief='raised', bd=4, padx=30, pady=10)
        confirm_btn.pack(side='right')
        
    def select_all_stocks(self, stock_vars):
        """Select all stocks in dialog"""
        for var in stock_vars.values():
            var.set(True)
    
    def deselect_all_stocks(self, stock_vars):
        """Deselect all stocks in dialog"""
        for var in stock_vars.values():
            var.set(False)
    
    def confirm_stock_selection(self, dialog, stock_vars, available_stocks):
        """Confirm stock selection and update display"""
        selected = [stock for stock, var in stock_vars.items() if var.get()]
        
        if not selected:
            messagebox.showwarning("Configuration Warning", "Please configure at least one stock!")
            return
        
        # Close configuration dialog first
        dialog.destroy()
        
        # Handle single stock selection
        if len(selected) == 1:
            stock = selected[0]
            self.selected_stock_symbols = selected
            self.update_portfolio_display()
            
            # Check ownership immediately for single stock
            if self.is_connected and self.session and self.headers:
                self.check_single_stock_ownership(stock)
            else:
                self.log_trading_message(f"CONFIG_SET: Configured stock {stock}. Connect to platform to verify ownership.")
        
        # Handle multiple stock selection
        else:
            self.selected_stock_symbols = selected
            self.update_portfolio_display()
            
            if self.is_connected and self.session and self.headers:
                # Show loading and check all stocks
                self.check_multiple_stocks_ownership(selected)
            else:
                if len(selected) <= 3:
                    self.log_trading_message(f"CONFIG_SET: Configured {len(selected)} stocks: {', '.join(selected)}")
                else:
                    self.log_trading_message(f"CONFIG_SET: Configured {len(selected)} stocks for dynamic trading")
                self.log_trading_message("SYSTEM_READY: Connect to platform to verify ownership")
    
    def update_portfolio_display(self):
        """Update portfolio display"""
        if not self.selected_stock_symbols:
            self.portfolio_label.config(text="No stocks configured")
            return
        
        # Handle different display cases based on number of stocks
        stock_count = len(self.selected_stock_symbols)
        
        if stock_count == 1:
            display_text = f"Configured: {self.selected_stock_symbols[0]}"
        elif stock_count <= 3:
            display_text = f"Dynamic portfolio ({stock_count}): {', '.join(self.selected_stock_symbols)}"
        else:
            first_three = ', '.join(self.selected_stock_symbols[:3])
            remaining = stock_count - 3
            display_text = f"Dynamic portfolio ({stock_count}): {first_three}... (+{remaining} more)"
        
        self.portfolio_label.config(text=display_text)
    
    def check_single_stock_ownership(self, stock_symbol):
        """Check ownership for single stock"""
        try:
            # Get owned stocks first
            owned_stocks = self.get_owned_stocks_list()
            if not owned_stocks:
                self.log_trading_message(f"VERIFICATION_WARNING: Unable to verify stock {stock_symbol}")
                return
                
            # Check ownership
            primary_id = self.stock_ids.get(stock_symbol)
            alt_ids = self.alternative_stock_ids.get(stock_symbol, [])
            all_ids_to_check = [primary_id] + alt_ids if primary_id else alt_ids
            
            stock_found = False
            for stock_id in all_ids_to_check:
                if stock_id and stock_id in owned_stocks:
                    stock_found = True
                    break
                    
            if stock_found:
                self.log_trading_message(f"STOCK_VERIFIED: Verified ownership of stock {stock_symbol}")
            else:
                self.log_trading_message(f"VERIFICATION_ERROR: Stock {stock_symbol} not found in current portfolio")
                
        except Exception as e:
            self.log_trading_message(f"VERIFICATION_ERROR: Stock verification for {stock_symbol} failed: {str(e)}")
    
    def check_multiple_stocks_ownership(self, stocks_list):
        """Check ownership for multiple stocks with loading"""
        # Show loading
        self.loading_frame.pack(pady=(15, 0))
        
        # Start check in background thread
        check_thread = threading.Thread(target=self._check_stocks_thread, args=(stocks_list,), daemon=True)
        check_thread.start()
    
    def _check_stocks_thread(self, stocks_list):
        """Background thread to check stock ownership"""
        try:
            # Get owned stocks
            owned_stocks = self.get_owned_stocks_list()
            if not owned_stocks:
                self.root.after(0, self._hide_loading)
                self.root.after(0, lambda: self.log_trading_message("VERIFICATION_WARNING: Unable to verify portfolio"))
                return
            
            # Check each stock
            missing_stocks = []
            for stock_symbol in stocks_list:
                primary_id = self.stock_ids.get(stock_symbol)
                alt_ids = self.alternative_stock_ids.get(stock_symbol, [])
                all_ids_to_check = [primary_id] + alt_ids if primary_id else alt_ids
                
                stock_found = False
                for stock_id in all_ids_to_check:
                    if stock_id and stock_id in owned_stocks:
                        stock_found = True
                        break
                        
                if not stock_found:
                    missing_stocks.append(stock_symbol)
            
            # Hide loading and show results
            self.root.after(0, self._hide_loading)
            
            if missing_stocks:
                # Show missing stocks dialog
                self.root.after(0, lambda: self._show_missing_stocks_dialog(missing_stocks))
            else:
                # All stocks owned
                if len(stocks_list) <= 3:
                    self.root.after(0, lambda: self.log_trading_message(f"PORTFOLIO_VERIFIED: Dynamic portfolio configured successfully: {', '.join(stocks_list)}"))
                else:
                    self.root.after(0, lambda: self.log_trading_message(f"PORTFOLIO_VERIFIED: Dynamic portfolio configured successfully ({len(stocks_list)} stocks)"))
                    
        except Exception as e:
            self.root.after(0, self._hide_loading)
            self.root.after(0, lambda: self.log_trading_message(f"VERIFICATION_ERROR: Portfolio verification error: {str(e)}"))
    
    def _hide_loading(self):
        """Hide loading indicator"""
        self.loading_frame.pack_forget()
    
    def _show_missing_stocks_dialog(self, missing_stocks):
        """Show dialog for missing stocks"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Portfolio Verification Warning")
        dialog.geometry("500x250")
        dialog.resizable(False, False)
        dialog.configure(bg='#1a2332')
        
        # Remove window icon
        try:
            dialog.iconbitmap('')
        except:
            pass
        
        # Center dialog
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Main frame
        main_frame = tk.Frame(dialog, bg='#1a2332')
        main_frame.pack(fill='both', expand=True, padx=25, pady=25)
        
        # Warning icon and title
        title_frame = tk.Frame(main_frame, bg='#1a2332')
        title_frame.pack(pady=(0, 20))
        
        title_label = tk.Label(title_frame, text="⚠️ Portfolio Verification Warning", 
                             bg='#1a2332', fg='#ff4444', font=('Segoe UI', 16, 'bold'))
        title_label.pack()
        
        # Message
        missing_text = ', '.join(missing_stocks)
        message_text = f"Stocks {missing_text} not found in current portfolio. System will automatically remove from configuration.\n\nReconfigure portfolio after acquiring additional stocks."
        
        message_label = tk.Label(main_frame, text=message_text,
                               bg='#1a2332', fg='#ffffff', font=('Segoe UI', 11),
                               wraplength=450, justify='center')
        message_label.pack(pady=(0, 25))
        
        # Close button
        close_btn = tk.Button(main_frame, text="ACKNOWLEDGE",
                            command=lambda: self._close_missing_dialog(dialog, missing_stocks),
                            font=('Segoe UI', 12, 'bold'), bg='#0066cc', fg='white',
                            activebackground='#0052a3', relief='raised', bd=3,
                            padx=35, pady=10)
        close_btn.pack()
    
    def _close_missing_dialog(self, dialog, missing_stocks):
        """Close missing stocks dialog and update selection"""
        dialog.destroy()
        
        # Remove missing stocks from selection
        remaining_stocks = [stock for stock in self.selected_stock_symbols if stock not in missing_stocks]
        self.selected_stock_symbols = remaining_stocks
        
        # Update display
        self.update_portfolio_display()
        
        # Log update
        if remaining_stocks:
            if len(remaining_stocks) <= 3:
                self.log_trading_message(f"PORTFOLIO_UPDATE: Configuration updated: {', '.join(remaining_stocks)}")
            else:
                self.log_trading_message(f"PORTFOLIO_UPDATE: Configuration updated ({len(remaining_stocks)} stocks)")
        else:
            self.log_trading_message("CONFIG_EMPTY: No stocks remaining. Please reconfigure portfolio!")
    
    def get_owned_stocks_list(self):
        """Get list of owned stock IDs"""
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
                        owned_stocks = []
                        
                        if isinstance(owned, list):
                            for stock in owned:
                                if isinstance(stock, dict):
                                    stock_id = stock.get('id') or stock.get('championId') or stock.get('itemId')
                                    if stock_id and stock.get('active', True):
                                        owned_stocks.append(stock_id)
                        elif isinstance(owned, dict) and 'champions' in owned:
                            for stock in owned['champions']:
                                stock_id = stock.get('id') or stock.get('championId') or stock.get('itemId')
                                if stock_id and stock.get('active', True):
                                    owned_stocks.append(stock_id)
                        
                        if owned_stocks:
                            return owned_stocks
                except Exception:
                    continue
            
            return []
        except Exception:
            return []
    
    def get_random_stock_from_selected(self):
        """Get random stock from selected list"""
        if not self.selected_stock_symbols:
            # Fallback for original behavior if no stocks selected
            return self.get_random_stock()
        
        return random.choice(self.selected_stock_symbols)


def main():
    root = tk.Tk()
    app = StockTradingPlatform(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        if app.is_trading_active:
            app.stop_trading_system()
        root.quit()


if __name__ == "__main__":
    main()
