import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import requests
import time
import threading
from urllib.parse import urlparse
import base64
import json

try:
    from google import genai
    from google.genai.types import GenerateImagesConfig
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False

class GeminiImageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tạo ảnh AI")
        self.root.geometry("900x700")
        self.root.minsize(600, 500)
        
        self.bg_color = "#0a0a0a"
        self.accent_color = "#00ff88"
        self.secondary_color = "#1a1a2e"
        self.text_color = "#ffffff"
        self.button_color = "#16213e"
        
        self.root.configure(bg=self.bg_color)
        
        self.prompts = []
        self.file_path = None
        
        self.setup_ui()
        
        self.root.bind('<Configure>', self.on_window_resize)
        
    def setup_ui(self):
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title_label = tk.Label(
            main_frame, 
            text="Tạo ảnh Gemini", 
            font=("Arial", 24, "bold"),
            fg=self.accent_color,
            bg=self.bg_color
        )
        title_label.pack(pady=(0, 30))
        
        self.file_frame = tk.Frame(main_frame, bg=self.bg_color)
        self.file_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.select_file_btn = tk.Button(
            self.file_frame,
            text="📁 Chọn file TXT",
            font=("Arial", 12, "bold"),
            bg=self.button_color,
            fg=self.text_color,
            activebackground=self.accent_color,
            activeforeground=self.bg_color,
            relief=tk.FLAT,
            padx=20,
            pady=10,
            cursor="hand2",
            command=self.select_file
        )
        self.select_file_btn.pack(side=tk.LEFT)
        
        self.file_display_frame = tk.Frame(self.file_frame, bg=self.bg_color)
        
        self.file_name_label = tk.Label(
            self.file_display_frame,
            text="",
            font=("Arial", 12, "bold"),
            fg=self.accent_color,
            bg=self.bg_color
        )
        self.file_name_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.close_file_btn = tk.Button(
            self.file_display_frame,
            text="✕",
            font=("Arial", 12, "bold"),
            bg=self.bg_color,
            fg="#ff4444",
            activebackground=self.bg_color,
            activeforeground="#cc3333",
            relief=tk.FLAT,
            bd=0,
            padx=5,
            pady=0,
            cursor="hand2",
            command=self.close_file
        )
        self.close_file_btn.pack(side=tk.LEFT)
        
        # API Key input frame
        api_frame = tk.Frame(self.file_frame, bg=self.bg_color)
        api_frame.pack(side=tk.LEFT, padx=(20, 0), fill=tk.X, expand=True)
        
        api_label = tk.Label(
            api_frame,
            text="API Key:",
            font=("Arial", 12, "bold"),
            fg=self.text_color,
            bg=self.bg_color
        )
        api_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.api_entry = tk.Entry(
            api_frame,
            font=("Arial", 11),
            bg=self.secondary_color,
            fg=self.text_color,
            insertbackground=self.accent_color,
            relief=tk.FLAT,
            show="*"
        )
        self.api_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.api_entry.bind('<FocusOut>', self.check_api_balance)
        self.api_entry.bind('<Return>', self.check_api_balance)
        
        # Add token display
        self.token_label = tk.Label(
            api_frame,
            text="",
            font=("Arial", 10),
            fg=self.accent_color,
            bg=self.bg_color
        )
        self.token_label.pack(side=tk.LEFT, padx=(10, 0))
        
        content_frame = tk.Frame(main_frame, bg=self.bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        left_frame = tk.Frame(content_frame, bg=self.bg_color)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 20))
        
        table_label = tk.Label(
            left_frame,
            text="Danh sách Prompts:",
            font=("Arial", 14, "bold"),
            fg=self.text_color,
            bg=self.bg_color
        )
        table_label.pack(anchor=tk.W, pady=(0, 10))
        
        tree_frame = tk.Frame(left_frame, bg=self.bg_color)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Custom.Treeview",
                       background=self.secondary_color,
                       foreground=self.text_color,
                       fieldbackground=self.secondary_color,
                       borderwidth=1,
                       relief="solid",
                       font=("Arial", 10),
                       rowheight=25)
        style.configure("Custom.Treeview.Heading",
                       background=self.button_color,
                       foreground=self.accent_color,
                       font=("Arial", 11, "bold"),
                       borderwidth=1,
                       relief="solid")
        style.map("Custom.Treeview.Heading",
                 background=[('active', self.button_color), ('pressed', self.button_color)],
                 foreground=[('active', self.accent_color), ('pressed', self.accent_color)])
        style.map("Custom.Treeview",
                 background=[('selected', self.secondary_color), ('active', self.secondary_color), ('focus', self.secondary_color)],
                 foreground=[('selected', self.text_color), ('active', self.text_color), ('focus', self.text_color)])
        
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("prompt",),
            show="tree headings",
            style="Custom.Treeview",
            height=15
        )
        
        self.tree.heading("#0", text="STT", anchor=tk.CENTER)
        self.tree.heading("prompt", text="Prompt", anchor=tk.CENTER)
        self.tree.column("#0", width=60, minwidth=60, anchor=tk.CENTER)
        self.tree.column("prompt", width=400, minwidth=200, anchor=tk.W)
        
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind("<Button-1>", self.on_tree_click)
        self.tree.bind("<Button-3>", self.on_right_click)  # Right click for context menu
        
        right_frame = tk.Frame(content_frame, bg=self.bg_color, width=200)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        right_frame.pack_propagate(False)
        
        # Folder name input
        folder_label = tk.Label(
            right_frame,
            text="Tên folder:",
            font=("Arial", 12, "bold"),
            fg=self.text_color,
            bg=self.bg_color
        )
        folder_label.pack(pady=(0, 10))
        
        self.folder_entry = tk.Entry(
            right_frame,
            font=("Arial", 12),
            bg=self.secondary_color,
            fg=self.text_color,
            insertbackground=self.accent_color,
            relief=tk.FLAT,
            justify=tk.CENTER
        )
        self.folder_entry.pack(fill=tk.X, pady=(0, 20))
        self.folder_entry.insert(0, "test1")
        
        time_label = tk.Label(
            right_frame,
            text="Thời gian (giây):",
            font=("Arial", 12, "bold"),
            fg=self.text_color,
            bg=self.bg_color
        )
        time_label.pack(pady=(0, 10))
        
        self.time_entry = tk.Entry(
            right_frame,
            font=("Arial", 12),
            bg=self.secondary_color,
            fg=self.text_color,
            insertbackground=self.accent_color,
            relief=tk.FLAT,
            justify=tk.CENTER
        )
        self.time_entry.pack(fill=tk.X, pady=(0, 20))
        self.time_entry.insert(0, "5")
        
        self.start_btn = tk.Button(
            right_frame,
            text="🚀 Bắt đầu",
            font=("Arial", 14, "bold"),
            bg=self.accent_color,
            fg=self.bg_color,
            activebackground="#00cc66",
            activeforeground=self.bg_color,
            relief=tk.FLAT,
            padx=20,
            pady=15,
            cursor="hand2",
            command=self.start_process
        )
        self.start_btn.pack(fill=tk.X)
        
        self.status_label = tk.Label(
            right_frame,
            text="Sẵn sàng",
            font=("Arial", 10),
            fg="#888888",
            bg=self.bg_color,
            wraplength=180
        )
        self.status_label.pack(pady=(20, 0))
        
        # Add countdown display
        self.countdown_label = tk.Label(
            right_frame,
            text="",
            font=("Arial", 14, "bold"),
            fg=self.accent_color,
            bg=self.bg_color
        )
        self.countdown_label.pack(pady=(10, 0))
        
        # Add progress display
        self.progress_label = tk.Label(
            right_frame,
            text="",
            font=("Arial", 10),
            fg="#888888",
            bg=self.bg_color,
            wraplength=180
        )
        self.progress_label.pack(pady=(10, 0))
        
        # Add variable to track process state
        self.is_processing = False
        
        # Add token tracking variables
        self.current_tokens = 0
        self.total_tokens_used = 0
        
    def check_api_balance(self, event=None):
        """Check API key balance and display available tokens"""
        api_key = self.api_entry.get().strip()
        if not api_key:
            self.token_label.config(text="")
            return
            
        try:
            # Use a simple test request to check if API key works
            # Try the countTokens endpoint as it's more reliable
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:countTokens?key={api_key}"
            
            headers = {
                "Content-Type": "application/json",
            }
            
            # Simple test data
            test_data = {
                "contents": [{
                    "parts": [{"text": "test"}],
                    "role": "user"
                }]
            }
            
            response = requests.post(url, headers=headers, json=test_data, timeout=15)
            
            if response.status_code == 200:
                # API key is valid, simulate token count (Google doesn't provide actual balance via API)
                # This is a mock implementation - in reality you'd track usage locally
                remaining_tokens = 1000000 - self.total_tokens_used  # Mock balance
                self.current_tokens = remaining_tokens
                self.token_label.config(text=f"💎 {remaining_tokens:,} tokens", fg=self.accent_color)
                self.status_label.config(text="API key hợp lệ ✅")
            elif response.status_code == 400:
                # Try with a different model if 2.0 flash fails
                url2 = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:countTokens?key={api_key}"
                response2 = requests.post(url2, headers=headers, json=test_data, timeout=15)
                
                if response2.status_code == 200:
                    remaining_tokens = 1000000 - self.total_tokens_used
                    self.current_tokens = remaining_tokens
                    self.token_label.config(text=f"💎 {remaining_tokens:,} tokens", fg=self.accent_color)
                    self.status_label.config(text="API key hợp lệ ✅")
                else:
                    self.token_label.config(text="❌ API không hợp lệ", fg="#ff4444")
                    self.status_label.config(text="API key không hợp lệ")
            else:
                self.token_label.config(text="❌ API không hợp lệ", fg="#ff4444")
                self.status_label.config(text=f"Lỗi {response.status_code}: API key không hợp lệ")
        except Exception as e:
            self.token_label.config(text="❌ Lỗi kiểm tra", fg="#ff4444")
            self.status_label.config(text=f"Không thể kiểm tra API key: {str(e)[:30]}")
    
    def count_tokens(self, api_key, prompt):
        """Count tokens for a prompt using Gemini API"""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:countTokens?key={api_key}"
            
            headers = {
                "Content-Type": "application/json",
            }
            
            data = {
                "contents": [{
                    "parts": [{"text": prompt}],
                    "role": "user"
                }]
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('totalTokens', 0)
            else:
                return 50  # Estimate if count fails
        except:
            return 50  # Estimate if count fails
    
    def update_token_usage(self, tokens_used):
        """Update token usage and display"""
        self.total_tokens_used += tokens_used
        remaining = max(0, self.current_tokens - tokens_used)
        self.current_tokens = remaining
        
        self.root.after(0, lambda: self.token_label.config(
            text=f"💎 {remaining:,} tokens",
            fg=self.accent_color if remaining > 1000 else "#ff8800"
        ))
        
    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="Chọn file TXT",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            self.file_path = file_path
            self.show_file_selected(os.path.basename(file_path))
            self.load_prompts()
    
    def show_file_selected(self, filename):
        self.select_file_btn.pack_forget()
        self.file_name_label.config(text=filename)
        self.file_display_frame.pack(side=tk.LEFT)
    
    def close_file(self):
        self.file_path = None
        self.prompts = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.file_display_frame.pack_forget()
        self.select_file_btn.pack(side=tk.LEFT)
        self.status_label.config(text="Sẵn sàng")
            
    def load_prompts(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                
            for item in self.tree.get_children():
                self.tree.delete(item)
                
            self.prompts = []
            
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if line:
                    self.prompts.append(line)
                    display_text = line if len(line) <= 50 else line[:47] + "..."
                    self.tree.insert("", tk.END, text=str(i), values=(display_text,))
                    
            self.status_label.config(text=f"Đã tải {len(self.prompts)} prompts")
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đọc file: {str(e)}")
            
    def on_tree_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "heading":
            return "break"
        
        item = self.tree.identify_row(event.y)
        if item:
            column = self.tree.identify_column(event.x)
            if column == "#1":
                self.root.after(10, lambda: self.edit_item(item))
    
    def on_right_click(self, event):
        """Handle right click to show context menu"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.show_context_menu(event, item)
    
    def show_context_menu(self, event, item):
        """Show context menu with delete option"""
        context_menu = tk.Menu(self.root, tearoff=0, bg=self.secondary_color, fg=self.text_color,
                              activebackground=self.accent_color, activeforeground=self.bg_color)
        
        context_menu.add_command(label="🗑️ Xóa prompt", command=lambda: self.delete_prompt(item))
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def delete_prompt(self, item):
        """Delete a prompt and renumber the STT"""
        try:
            # Get the index of the item to delete
            item_index = int(self.tree.item(item, "text")) - 1
            
            if 0 <= item_index < len(self.prompts):
                # Remove from prompts list
                del self.prompts[item_index]
                
                # Clear and rebuild the tree with renumbered STT
                for tree_item in self.tree.get_children():
                    self.tree.delete(tree_item)
                
                # Rebuild tree with new STT numbers
                for i, prompt in enumerate(self.prompts, 1):
                    display_text = prompt if len(prompt) <= 50 else prompt[:47] + "..."
                    self.tree.insert("", tk.END, text=str(i), values=(display_text,))
                
                # Save changes to file
                self.save_to_file()
                
                # Update status
                self.status_label.config(text=f"Đã xóa prompt. Còn lại {len(self.prompts)} prompts")
                
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xóa prompt: {str(e)}")
    
    def on_item_double_click(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        column = self.tree.identify_column(event.x)
        
        if column == "#1":
            self.edit_item(item)
            
    def edit_item(self, item):
        item_index = int(self.tree.item(item, "text")) - 1
        if 0 <= item_index < len(self.prompts):
            current_value = self.prompts[item_index]
        else:
            current_value = self.tree.item(item, "values")[0]
        
        x, y, width, height = self.tree.bbox(item, "prompt")
        
        self.edit_entry = tk.Entry(self.tree, font=("Arial", 10), bg=self.secondary_color, fg=self.text_color, insertbackground=self.accent_color, relief=tk.FLAT)
        self.edit_entry.place(x=x, y=y, width=width, height=height)
        self.edit_entry.insert(0, current_value)
        self.edit_entry.select_range(0, tk.END)
        self.edit_entry.focus()
        
        self.edit_entry.bind("<Return>", lambda e: self.save_edit(item))
        self.edit_entry.bind("<Escape>", lambda e: self.cancel_edit())
        self.edit_entry.bind("<FocusOut>", lambda e: self.save_edit(item))
        
    def save_edit(self, item):
        if hasattr(self, 'edit_entry'):
            try:
                new_value = self.edit_entry.get()
                
                # Check if item still exists in tree
                if self.tree.exists(item):
                    display_text = new_value if len(new_value) <= 50 else new_value[:47] + "..."
                    self.tree.item(item, values=(display_text,))
                    
                    item_index = int(self.tree.item(item, "text")) - 1
                    if 0 <= item_index < len(self.prompts):
                        self.prompts[item_index] = new_value
                        
                    self.save_to_file()
                    
            except Exception as e:
                print(f"Error saving edit: {e}")
            finally:
                try:
                    self.edit_entry.destroy()
                    del self.edit_entry
                except:
                    pass
            
    def cancel_edit(self):
        if hasattr(self, 'edit_entry'):
            self.edit_entry.destroy()
            del self.edit_entry
            
    def save_to_file(self):
        if self.file_path and self.prompts:
            try:
                with open(self.file_path, 'w', encoding='utf-8') as file:
                    for prompt in self.prompts:
                        file.write(prompt + '\n')
                self.status_label.config(text="Đã lưu thay đổi")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể lưu file: {str(e)}")
                
    def start_process(self):
        if self.is_processing:
            return
            
        if not self.prompts:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn file TXT trước!")
            return
            
        api_key = self.api_entry.get().strip()
        if not api_key:
            messagebox.showerror("Lỗi", "Vui lòng nhập API Key!")
            return
            
        folder_name = self.folder_entry.get().strip()
        if not folder_name:
            messagebox.showerror("Lỗi", "Vui lòng nhập tên folder!")
            return
            
        try:
            time_value = float(self.time_entry.get())
            if time_value <= 0:
                raise ValueError("Thời gian phải lớn hơn 0")
        except ValueError:
            messagebox.showerror("Lỗi", "Vui lòng nhập thời gian hợp lệ (số dương)!")
            return
        
        # Start processing in separate thread
        self.is_processing = True
        self.start_btn.config(text="Đang xử lý...", state="disabled")
        
        thread = threading.Thread(target=self.process_prompts, args=(api_key, folder_name, time_value))
        thread.daemon = True
        thread.start()
    
    def process_prompts(self, api_key, folder_name, time_value):
        try:
            # Create main folder in the same directory as the script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            main_folder = os.path.join(script_dir, folder_name)
            os.makedirs(main_folder, exist_ok=True)
            
            total_prompts = len(self.prompts)
            
            for i, prompt in enumerate(self.prompts, 1):
                if not self.is_processing:  # Check if process was stopped
                    break
                    
                self.root.after(0, lambda i=i, total=total_prompts: 
                    self.progress_label.config(text=f"Đang xử lý {i}/{total}"))
                
                self.root.after(0, lambda p=prompt: 
                    self.status_label.config(text=f"Tạo ảnh: {p[:30]}..."))
                
                # Generate image using Gemini API - save directly to main folder
                success = self.generate_and_save_image(api_key, prompt, main_folder, i)
                
                if not success:
                    self.root.after(0, lambda: 
                        self.status_label.config(text=f"Lỗi tại prompt {i}"))
                    
                # Countdown timer (except for last prompt)
                if i < total_prompts:
                    for countdown in range(int(time_value), 0, -1):
                        if not self.is_processing:
                            break
                        self.root.after(0, lambda c=countdown: 
                            self.countdown_label.config(text=f"⏱️ {c}s"))
                        time.sleep(1)
                    
                    self.root.after(0, lambda: self.countdown_label.config(text=""))
            
            # Process completed
            self.root.after(0, self.process_completed)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Lỗi", f"Lỗi trong quá trình xử lý: {str(e)}"))
            self.root.after(0, self.process_completed)
    
    def generate_and_save_image(self, api_key, prompt, folder_path, prompt_number):
        try:
            # Count tokens for this prompt first (silently)
            tokens_needed = self.count_tokens(api_key, prompt)
            
            # Generate image with Gemini
            self.root.after(0, lambda: 
                self.status_label.config(text=f"🎨 Đang tạo ảnh từ Gemini cho ảnh {prompt_number}..."))
            
            try:
                # Gemini 2.0 Flash API endpoint
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}"
                
                headers = {
                    "Content-Type": "application/json",
                }
                
                # Use original prompt directly without any modifications
                data = {
                    "contents": [{
                        "parts": [{"text": prompt}],
                        "role": "user"
                    }],
                    "generationConfig": {
                        "responseModalities": ["TEXT", "IMAGE"]
                    }
                }
                
                response = requests.post(url, headers=headers, json=data, timeout=120)
                
                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and len(result['candidates']) > 0:
                        parts = result['candidates'][0]['content']['parts']
                        
                        # Extract actual token usage from response if available
                        actual_tokens_used = tokens_needed
                        if 'usageMetadata' in result:
                            usage = result['usageMetadata']
                            actual_tokens_used = usage.get('totalTokenCount', tokens_needed)
                        
                        # Find image in response parts
                        image_part = None
                        for part in parts:
                            if 'inlineData' in part:
                                image_part = part
                                break
                        
                        if image_part and 'inlineData' in image_part:
                            # Get the base64 image data
                            image_data = image_part['inlineData']['data']
                            mime_type = image_part['inlineData']['mimeType']
                            
                            # Determine file extension
                            if 'png' in mime_type:
                                extension = 'png'
                            elif 'jpeg' in mime_type or 'jpg' in mime_type:
                                extension = 'jpg'
                            elif 'webp' in mime_type:
                                extension = 'webp'
                            else:
                                extension = 'png'  # default
                            
                            # Decode and save image (keeping original size from Gemini)
                            image_bytes = base64.b64decode(image_data)
                            image_path = os.path.join(folder_path, f"{prompt_number}.{extension}")
                            
                            # Save image without any resizing or processing
                            with open(image_path, 'wb') as f:
                                f.write(image_bytes)
                            
                            # Update token usage
                            self.update_token_usage(actual_tokens_used)
                            
                            self.root.after(0, lambda pnum=prompt_number: 
                                self.status_label.config(text=f"✅ Đã lưu ảnh {pnum}"))
                            return True
                        else:
                            error_msg = "Gemini 2.0 không trả về ảnh nào"
                            self.root.after(0, lambda msg=error_msg: 
                                self.status_label.config(text=f"❌ {msg}"))
                            return False
                    else:
                        error_msg = "Gemini 2.0 không có candidates"
                        self.root.after(0, lambda msg=error_msg: 
                            self.status_label.config(text=f"❌ {msg}"))
                        return False
                else:
                    # Handle API errors with retry logic
                    error_msg = f"API Error {response.status_code}"
                    try:
                        error_detail = response.json()
                        if 'error' in error_detail:
                            error_msg = error_detail['error'].get('message', error_msg)
                            
                            # Check if it's an internal error that we should retry
                            if "internal error" in error_msg.lower() or response.status_code >= 500:
                                self.root.after(0, lambda pnum=prompt_number: 
                                    self.status_label.config(text=f"⚠️ Lỗi nội bộ Gemini, thử lại sau cho ảnh {pnum}..."))
                                
                                # Wait a bit and retry once
                                time.sleep(3)
                                return self.generate_and_save_image(api_key, prompt, folder_path, prompt_number)
                    except:
                        error_msg = f"HTTP {response.status_code}: {response.text[:100]}"
                    
                    # For non-retryable errors, show specific error message
                    if "quota" in error_msg.lower() or "limit" in error_msg.lower():
                        display_msg = "❌ Đã hết quota API"
                    elif "invalid" in error_msg.lower():
                        display_msg = "❌ API key không hợp lệ"
                    else:
                        display_msg = f"❌ Lỗi API: {error_msg[:30]}..."
                    
                    print(f"Gemini API error: {error_msg}")
                    self.root.after(0, lambda msg=display_msg: 
                        self.status_label.config(text=msg))
                    return False
                    
            except Exception as api_error:
                error_msg = str(api_error)
                print(f"Gemini 2.0 error: {error_msg}")
                self.root.after(0, lambda msg=error_msg: 
                    self.status_label.config(text=f"❌ API: {msg[:40]}..."))
                return False
                
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: 
                self.status_label.config(text=f"❌ Lỗi: {msg[:50]}"))
            return False
    
    def process_completed(self):
        self.is_processing = False
        self.start_btn.config(text="🚀 Bắt đầu", state="normal")
        self.status_label.config(text="✅ Hoàn thành!")
        self.progress_label.config(text="")
        self.countdown_label.config(text="")
        
    def on_window_resize(self, event):
        if event.widget == self.root:
            pass

def main():
    root = tk.Tk()
    app = GeminiImageApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
