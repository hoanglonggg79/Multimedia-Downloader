"""
MULTIMEDIA DOWNLOADER
Version: 1.0.0

Built with:
- yt-dlp by yt-dlp team
- FFmpeg by FFmpeg team  
- CustomTkinter by Tom Schimansky
- Pygame by Pygame Community

Copyright (c) 2026 HoangLong
Licensed under MIT License
"""

import customtkinter as ctk
import subprocess
import threading
import os
import re
import json
from tkinter import filedialog, messagebox
import pygame
from pathlib import Path

# Cấu hình giao diện
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class LanguageManager:
    def __init__(self, language_folder="language"):
        self.language_folder = language_folder
        self.languages = {}
        self.current_language = "en"  # Ngôn ngữ mặc định là tiếng Anh
        self.load_all_languages()
    
    def load_all_languages(self):
        """Tự động load tất cả file .json trong thư mục language"""
        if not os.path.exists(self.language_folder):
            print(f"Warning: Language folder '{self.language_folder}' not found!")
            return
        
        json_files = [f for f in os.listdir(self.language_folder) if f.endswith('.json')]
        
        if not json_files:
            print(f"Warning: No language files found in '{self.language_folder}'!")
            return
        
        for file in json_files:
            lang_code = file.replace('.json', '')
            try:
                file_path = os.path.join(self.language_folder, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.languages[lang_code] = json.load(f)
                print(f"Loaded language: {lang_code}")
            except Exception as e:
                print(f"Error loading language file {file}: {e}")
        
        # Kiểm tra xem có ngôn ngữ nào được load không
        if not self.languages:
            print("Critical: No languages loaded! App may not display text correctly.")
    
    def get_text(self, key, default=None):
        """Lấy text theo ngôn ngữ hiện tại với fallback"""
        # Thử lấy từ ngôn ngữ hiện tại
        text = self.languages.get(self.current_language, {}).get(key)
        
        # Nếu không có, thử fallback sang tiếng Anh
        if text is None and self.current_language != "en":
            text = self.languages.get("en", {}).get(key)
        
        # Nếu vẫn không có, trả về default hoặc key
        if text is None:
            return default if default is not None else key
        
        return text
    
    def set_language(self, lang_code):
        """Đổi ngôn ngữ"""
        if lang_code in self.languages:
            self.current_language = lang_code
            return True
        print(f"Warning: Language '{lang_code}' not found!")
        return False
    
    def get_available_languages(self):
        """Lấy danh sách ngôn ngữ khả dụng"""
        return sorted(list(self.languages.keys()))

class MusicPlayer:
    def __init__(self, music_path="assets/music/theme.mp3"):
        self.music_path = music_path
        self.volume = 0.5
        self.is_initialized = False
        
        try:
            pygame.mixer.init()
            self.is_initialized = True
            
            # Kiểm tra file nhạc
            if os.path.exists(music_path):
                self.load_music()
            else:
                os.makedirs(os.path.dirname(music_path), exist_ok=True)
                print(f"Music file not found: {music_path}")
        except Exception as e:
            print(f"Failed to initialize music player: {e}")
    
    def load_music(self):
        """Load nhạc nền"""
        if not self.is_initialized:
            return
        
        try:
            pygame.mixer.music.load(self.music_path)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play(-1)
        except Exception as e:
            print(f"Cannot load music: {e}")
    
    def set_volume(self, volume):
        """Điều chỉnh âm lượng (0.0 - 1.0)"""
        if not self.is_initialized:
            return
        
        self.volume = max(0.0, min(1.0, volume))
        try:
            pygame.mixer.music.set_volume(self.volume)
        except:
            pass
    
    def pause(self):
        if self.is_initialized:
            try:
                pygame.mixer.music.pause()
            except:
                pass
    
    def unpause(self):
        if self.is_initialized:
            try:
                pygame.mixer.music.unpause()
            except:
                pass
    
    def stop(self):
        if self.is_initialized:
            try:
                pygame.mixer.music.stop()
            except:
                pass

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Khởi tạo Language Manager
        self.lang_manager = LanguageManager()
        
        # Khởi tạo Music Player
        self.music_player = MusicPlayer()

        # File lưu cấu hình
        self.config_file = "downloader_config.json"
        config = self.load_config()
        self.save_path = config.get('save_path', os.path.join(os.path.expanduser("~"), "Downloads"))
        
        # Load ngôn ngữ từ config, fallback sang 'en' nếu không hợp lệ
        saved_lang = config.get('language', 'en')
        if saved_lang in self.lang_manager.languages:
            self.lang_manager.current_language = saved_lang
        else:
            self.lang_manager.current_language = 'en'
        
        self.music_player.volume = config.get('volume', 0.5)
        self.music_player.set_volume(self.music_player.volume)

        self.title(self.lang_manager.get_text("app_title", "Multimedia Downloader"))
        self.geometry("700x900")

        # Đường dẫn yt-dlp
        self.ytdlp_path = os.path.join("update", "yt-dlp.exe")
        
        # Tạo thư mục update nếu chưa có
        os.makedirs("update", exist_ok=True)

        # Biến để lưu danh sách file (cache)
        self.cached_files = []
        
        self.create_widgets()
        
        # Auto update khi khởi động
        self.auto_update_on_start()

    def create_widgets(self):
        """Tạo giao diện"""
        # --- Header với ngôn ngữ, âm lượng và update ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=10, pady=5)
        
        # Ngôn ngữ
        lang_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        lang_frame.pack(side="left", padx=10)
        
        self.lang_label = ctk.CTkLabel(lang_frame, text=self.lang_manager.get_text("language", "Language:"), font=("Arial", 10))
        self.lang_label.pack(side="left", padx=5)
        
        available_langs = self.lang_manager.get_available_languages()
        self.lang_combo = ctk.CTkComboBox(lang_frame, 
                                          values=available_langs if available_langs else ["en"], 
                                          width=100, 
                                          command=self.change_language)
        self.lang_combo.set(self.lang_manager.current_language)
        self.lang_combo.pack(side="left")
        
        # Nút Update
        self.btn_update = ctk.CTkButton(self.header_frame, 
                                        text=self.lang_manager.get_text("update_system", "Update System"),
                                        width=120, height=28,
                                        fg_color="#27ae60",
                                        command=self.manual_update)
        self.btn_update.pack(side="right", padx=10)
        
        # Âm lượng
        volume_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        volume_frame.pack(side="right", padx=10)
        
        self.volume_text_label = ctk.CTkLabel(volume_frame, text=self.lang_manager.get_text("volume", "Volume:"), font=("Arial", 10))
        self.volume_text_label.pack(side="left", padx=5)
        
        self.volume_slider = ctk.CTkSlider(volume_frame, from_=0, to=100, width=150, 
                                          command=self.change_volume)
        self.volume_slider.set(self.music_player.volume * 100)
        self.volume_slider.pack(side="left", padx=5)
        
        self.volume_label = ctk.CTkLabel(volume_frame, text=f"{int(self.music_player.volume * 100)}%", width=40)
        self.volume_label.pack(side="left")

        # --- Label trạng thái update ---
        self.update_status_label = ctk.CTkLabel(self, text="", font=("Arial", 9), text_color="gray")
        self.update_status_label.pack(pady=2)

        # --- Tiêu đề chính ---
        self.label_title = ctk.CTkLabel(self, text=self.lang_manager.get_text("main_title", "MULTIMEDIA DOWNLOADER"), 
                                       font=("Arial", 24, "bold"))
        self.label_title.pack(pady=15)

        # --- Nhập Link ---
        self.url_entry = ctk.CTkEntry(self, width=600, 
                                      placeholder_text=self.lang_manager.get_text("url_placeholder", "Paste link here..."))
        self.url_entry.pack(pady=5)
        self.url_entry.bind("<KeyRelease>", self.check_playlist)

        # --- Thông báo Playlist ---
        self.playlist_notice_label = ctk.CTkLabel(self, text="", font=("Arial", 11), text_color="orange")
        self.playlist_notice_label.pack(pady=2)

        # --- Nhập Tên File ---
        self.filename_entry = ctk.CTkEntry(self, width=600, 
                                          placeholder_text=self.lang_manager.get_text("filename_placeholder", "Set filename (leave empty for original name)"))
        self.filename_entry.pack(pady=10)

        # --- Chọn Chế độ: Video hay Audio ---
        self.mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.mode_frame.pack(pady=10)
        
        self.download_mode = ctk.StringVar(value="video")
        self.video_radio = ctk.CTkRadioButton(self.mode_frame, 
                                              text=self.lang_manager.get_text("video_mode", "Download Video (MP4)"), 
                                              variable=self.download_mode, value="video",
                                              command=self.mode_changed)
        self.video_radio.pack(side="left", padx=20)
        
        self.audio_radio = ctk.CTkRadioButton(self.mode_frame, 
                                              text=self.lang_manager.get_text("audio_mode", "Download Audio (MP3)"), 
                                              variable=self.download_mode, value="audio",
                                              command=self.mode_changed)
        self.audio_radio.pack(side="left", padx=20)

        # --- Checkbox giữ file gốc ---
        self.keep_original = ctk.BooleanVar(value=False)
        self.keep_checkbox = ctk.CTkCheckBox(self, 
                                             text=self.lang_manager.get_text("keep_original", "Keep original file (.webm) after converting to MP3"), 
                                             variable=self.keep_original)
        self.keep_checkbox.pack(pady=5)

        # --- Chọn chất lượng ---
        self.quality_combo = ctk.CTkComboBox(self, values=["1080p", "720p", "480p", "360p"], width=200)
        self.quality_combo.set("1080p")
        self.quality_combo.pack(pady=5)

        # --- Ước tính dung lượng ---
        self.size_estimate_label = ctk.CTkLabel(self, text="", font=("Arial", 10), text_color="gray")
        self.size_estimate_label.pack(pady=2)

        # --- Chọn nơi lưu ---
        self.path_frame = ctk.CTkFrame(self)
        self.path_frame.pack(pady=10, padx=50, fill="x")
        self.path_label = ctk.CTkLabel(self.path_frame, 
                                       text=f"{self.lang_manager.get_text('save_location', 'Save to:')} {self.save_path}", 
                                       font=("Arial", 10))
        self.path_label.pack(side="left", padx=10)
        self.btn_browse = ctk.CTkButton(self.path_frame, 
                                        text=self.lang_manager.get_text("change_path", "Change"), 
                                        width=80, command=self.browse_path)
        self.btn_browse.pack(side="right", padx=10, pady=5)

        # --- Tiến trình ---
        self.status_label = ctk.CTkLabel(self, text=self.lang_manager.get_text("ready", "Ready"), 
                                        font=("Arial", 12), text_color="cyan")
        self.status_label.pack(pady=(10, 0))
        
        self.progress_bar = ctk.CTkProgressBar(self, width=600)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

        # --- Nút Bắt đầu ---
        self.btn_start = ctk.CTkButton(self, text=self.lang_manager.get_text("start_download", "START DOWNLOAD"), 
                                       width=200, height=45, 
                                       fg_color="#1f6aa5", font=("Arial", 14, "bold"), 
                                       command=self.start_thread)
        self.btn_start.pack(pady=20)

        # --- Quản lý File ---
        self.create_file_manager()

    def create_file_manager(self):
        """Tạo phần quản lý file đã tải"""
        separator = ctk.CTkFrame(self, height=2, fg_color="gray")
        separator.pack(fill="x", padx=50, pady=10)
        
        self.manager_label = ctk.CTkLabel(self, text=self.lang_manager.get_text("file_manager", "DOWNLOADED FILES MANAGER"), 
                                         font=("Arial", 16, "bold"))
        self.manager_label.pack(pady=5)
        
        # Nút điều khiển
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=5)
        
        self.btn_refresh = ctk.CTkButton(btn_frame, text=self.lang_manager.get_text("refresh", "Refresh"), 
                                        width=100, command=self.refresh_file_list)
        self.btn_refresh.pack(side="left", padx=5)
        
        self.btn_open_folder = ctk.CTkButton(btn_frame, text=self.lang_manager.get_text("open_folder", "Open Folder"), 
                                            width=120, command=self.open_download_folder)
        self.btn_open_folder.pack(side="left", padx=5)
        
        self.btn_delete = ctk.CTkButton(btn_frame, text=self.lang_manager.get_text("delete_selected", "Delete Selected Files"), 
                                       width=150, fg_color="#e74c3c", 
                                       command=self.delete_selected_files)
        self.btn_delete.pack(side="left", padx=5)
        
        # Danh sách file
        self.file_listbox = ctk.CTkTextbox(self, width=600, height=150)
        self.file_listbox.pack(pady=10, padx=20)
        
        self.refresh_file_list()

    def refresh_file_list(self):
        """Làm mới danh sách file"""
        self.file_listbox.delete("1.0", "end")
        self.cached_files = []
        
        if not os.path.exists(self.save_path):
            self.file_listbox.insert("1.0", self.lang_manager.get_text("folder_not_found", "Folder not found!"))
            return
        
        try:
            # Lấy danh sách file với extension hợp lệ
            all_files = os.listdir(self.save_path)
            files = [f for f in all_files if f.lower().endswith(('.mp4', '.mp3', '.webm', '.m4a'))]
            
            if not files:
                self.file_listbox.insert("1.0", self.lang_manager.get_text("no_files", "No downloaded files yet!"))
                return
            
            # Sắp xếp theo thời gian sửa đổi (mới nhất trước)
            files.sort(key=lambda x: os.path.getmtime(os.path.join(self.save_path, x)), reverse=True)
            
            for i, file in enumerate(files, 1):
                file_path = os.path.join(self.save_path, file)
                try:
                    size = os.path.getsize(file_path) / (1024 * 1024)
                    self.file_listbox.insert("end", f"[{i}] {file} ({size:.2f} MB)\n")
                    self.cached_files.append(file)
                except Exception as e:
                    print(f"Error reading file {file}: {e}")
                    
        except Exception as e:
            self.file_listbox.insert("1.0", f"Error: {str(e)}")
            print(f"Error refreshing file list: {e}")

    def open_download_folder(self):
        """Mở thư mục chứa file đã tải"""
        if os.path.exists(self.save_path):
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(self.save_path)
                elif os.name == 'posix':  # macOS, Linux
                    subprocess.Popen(['xdg-open', self.save_path])
            except Exception as e:
                print(f"Cannot open folder: {e}")
                messagebox.showerror("Error", f"Cannot open folder: {e}")

    def delete_selected_files(self):
        """Xóa các file đã chọn"""
        selected_text = self.file_listbox.get("1.0", "end")
        
        files_to_delete = []
        for line in selected_text.split('\n'):
            line = line.strip()
            if line and line.startswith('['):
                try:
                    # Parse filename từ format: [1] filename.mp4 (5.23 MB)
                    match = re.match(r'\[\d+\]\s+(.+?)\s+\(\d+\.\d+\s+MB\)', line)
                    if match:
                        filename = match.group(1)
                        files_to_delete.append(filename)
                except Exception as e:
                    print(f"Error parsing line: {line}, Error: {e}")
                    continue
        
        if not files_to_delete:
            messagebox.showwarning(
                self.lang_manager.get_text("no_files_selected", "No files selected"),
                self.lang_manager.get_text("no_files_selected", "No files selected to delete!")
            )
            return
        
        confirm = messagebox.askyesno(
            self.lang_manager.get_text("confirm_delete", "Confirm Delete"),
            self.lang_manager.get_text("confirm_delete_msg", "Are you sure you want to delete {} selected files?").format(len(files_to_delete))
        )
        
        if confirm:
            deleted_count = 0
            for filename in files_to_delete:
                try:
                    file_path = os.path.join(self.save_path, filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        deleted_count += 1
                except Exception as e:
                    print(f"Cannot delete {filename}: {e}")
            
            messagebox.showinfo(
                self.lang_manager.get_text("success", "Success"),
                self.lang_manager.get_text("deleted_success", "Deleted {} files successfully!").format(deleted_count)
            )
            self.refresh_file_list()

    def check_playlist(self, event=None):
        """Kiểm tra xem link có phải playlist không"""
        url = self.url_entry.get().strip()
        if "playlist" in url.lower() or "list=" in url:
            self.playlist_notice_label.configure(
                text=self.lang_manager.get_text("playlist_detected", "Playlist detected! Will download entire playlist.")
            )
        else:
            self.playlist_notice_label.configure(text="")

    def mode_changed(self):
        """Xử lý khi đổi chế độ tải"""
        self.size_estimate_label.configure(text="")

    def update_all_texts(self):
        """Cập nhật toàn bộ text trong giao diện"""
        self.title(self.lang_manager.get_text("app_title", "Multimedia Downloader"))
        self.label_title.configure(text=self.lang_manager.get_text("main_title", "MULTIMEDIA DOWNLOADER"))
        self.url_entry.configure(placeholder_text=self.lang_manager.get_text("url_placeholder", "Paste link here..."))
        self.filename_entry.configure(placeholder_text=self.lang_manager.get_text("filename_placeholder", "Set filename (leave empty for original name)"))
        self.video_radio.configure(text=self.lang_manager.get_text("video_mode", "Download Video (MP4)"))
        self.audio_radio.configure(text=self.lang_manager.get_text("audio_mode", "Download Audio (MP3)"))
        self.keep_checkbox.configure(text=self.lang_manager.get_text("keep_original", "Keep original file (.webm) after converting to MP3"))
        self.path_label.configure(text=f"{self.lang_manager.get_text('save_location', 'Save to:')} {self.save_path}")
        self.btn_browse.configure(text=self.lang_manager.get_text("change_path", "Change"))
        self.status_label.configure(text=self.lang_manager.get_text("ready", "Ready"))
        self.btn_start.configure(text=self.lang_manager.get_text("start_download", "START DOWNLOAD"))
        self.btn_update.configure(text=self.lang_manager.get_text("update_system", "Update System"))
        
        #  header labels
        self.lang_label.configure(text=self.lang_manager.get_text("language", "Language:"))
        self.volume_text_label.configure(text=self.lang_manager.get_text("volume", "Volume:"))
        
        #  file manager
        self.manager_label.configure(text=self.lang_manager.get_text("file_manager", "DOWNLOADED FILES MANAGER"))
        self.btn_refresh.configure(text=self.lang_manager.get_text("refresh", "Refresh"))
        self.btn_open_folder.configure(text=self.lang_manager.get_text("open_folder", "Open Folder"))
        self.btn_delete.configure(text=self.lang_manager.get_text("delete_selected", "Delete Selected Files"))
        
        # Refresh file list để cập nhật text trong listbox
        self.refresh_file_list()

    def change_language(self, lang_code):
        """Đổi ngôn ngữ ngay lập tức"""
        if self.lang_manager.set_language(lang_code):
            self.save_config_data()
            self.update_all_texts()

    def change_volume(self, value):
        """Thay đổi âm lượng"""
        volume = float(value) / 100
        self.music_player.set_volume(volume)
        self.volume_label.configure(text=f"{int(value)}%")
        self.save_config_data()

    def auto_update_on_start(self):
        """Tự động update khi khởi động app"""
        threading.Thread(target=self._perform_update, args=(True,), daemon=True).start()

    def manual_update(self):
        """Update thủ công"""
        threading.Thread(target=self._perform_update, args=(False,), daemon=True).start()

    def _perform_update(self, silent=False):
        """Thực hiện update yt-dlp"""
        try:
            if not silent:
                self.btn_update.configure(state="disabled", text=self.lang_manager.get_text("updating", "Updating..."))
            
            self.update_status_label.configure(
                text=self.lang_manager.get_text("checking_update", "Checking for updates..."),
                text_color="yellow"
            )
            
            # Tải yt-dlp mới nhất nếu chưa có
            if not os.path.exists(self.ytdlp_path):
                try:
                    import urllib.request
                    url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
                    urllib.request.urlretrieve(url, self.ytdlp_path)
                except Exception as e:
                    print(f"Download yt-dlp failed: {e}")
                    if not silent:
                        self.update_status_label.configure(
                            text=self.lang_manager.get_text("update_failed", "Update failed!"),
                            text_color="red"
                        )
                    return
            
            # Update yt-dlp
            result = subprocess.run(
                [self.ytdlp_path, "-U"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                timeout=30  # Timeout 30 giây
            )
            
            if not silent:
                if result.returncode == 0:
                    self.update_status_label.configure(
                        text=self.lang_manager.get_text("update_success", "Update successful!"),
                        text_color="#2ecc71"
                    )
                else:
                    self.update_status_label.configure(
                        text=self.lang_manager.get_text("update_success", "Update successful!"),
                        text_color="#2ecc71"
                    )
            else:
                self.update_status_label.configure(text="", text_color="gray")
            
        except subprocess.TimeoutExpired:
            print("Update timeout")
            if not silent:
                self.update_status_label.configure(
                    text=self.lang_manager.get_text("update_failed", "Update failed!"),
                    text_color="red"
                )
        except Exception as e:
            print(f"Update error: {e}")
            if not silent:
                self.update_status_label.configure(
                    text=self.lang_manager.get_text("update_failed", "Update failed!"),
                    text_color="red"
                )
        finally:
            if not silent:
                self.btn_update.configure(state="normal", text=self.lang_manager.get_text("update_system", "Update System"))

    def load_config(self):
        """Đọc cấu hình"""
        default_config = {
            'save_path': os.path.join(os.path.expanduser("~"), "Downloads"),
            'language': 'en',
            'volume': 0.5
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge với default config
                    default_config.update(loaded_config)
        except Exception as e:
            print(f"Cannot load config: {e}")
        
        return default_config

    def save_config_data(self):
        """Lưu cấu hình"""
        try:
            config = {
                'save_path': self.save_path,
                'language': self.lang_manager.current_language,
                'volume': self.music_player.volume
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Cannot save config: {e}")

    def browse_path(self):
        """Chọn thư mục lưu file"""
        path = filedialog.askdirectory()
        if path:
            self.save_path = path
            self.path_label.configure(
                text=f"{self.lang_manager.get_text('save_location', 'Save to:')} {self.save_path}"
            )
            self.save_config_data()
            self.refresh_file_list()

    def estimate_file_size(self, url):
        """Ước tính dung lượng file"""
        try:
            self.size_estimate_label.configure(
                text=self.lang_manager.get_text("estimating", "Estimating size..."),
                text_color="yellow"
            )
            
            cmd = [
                self.ytdlp_path,
                '--dump-json',
                '--no-warnings',
                url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                timeout=10  # Timeout 10 giây
            )
            
            if result.returncode == 0 and result.stdout:
                info = json.loads(result.stdout)
                if 'filesize' in info and info['filesize']:
                    size_mb = info['filesize'] / (1024 * 1024)
                    self.size_estimate_label.configure(
                        text=f"{self.lang_manager.get_text('estimated_size', 'Estimated size:')} {size_mb:.2f} MB",
                        text_color="cyan"
                    )
                else:
                    self.size_estimate_label.configure(
                        text=self.lang_manager.get_text("estimated_size", "Estimated size:") + " ~50-200 MB",
                        text_color="gray"
                    )
        except subprocess.TimeoutExpired:
            self.size_estimate_label.configure(text="", text_color="gray")
        except Exception as e:
            print(f"Estimate error: {e}")
            self.size_estimate_label.configure(text="", text_color="gray")

    def start_thread(self):
        """Bắt đầu tải (thread)"""
        self.progress_bar.set(0)
        url = self.url_entry.get().strip()
        
        if not url:
            self.status_label.configure(
                text=self.lang_manager.get_text("error_no_link", "ERROR: Please paste a link!"), 
                text_color="red"
            )
            return

        # Estimate size trong thread riêng
        threading.Thread(target=self.estimate_file_size, args=(url,), daemon=True).start()
        
        # Start download
        thread = threading.Thread(target=self.download_process, args=(url,), daemon=True)
        thread.start()

    def download_process(self, url):
        """Xử lý tải xuống"""
        self.btn_start.configure(state="disabled")
        
        custom_name = self.filename_entry.get().strip()
        # Sanitize filename - loại bỏ ký tự không hợp lệ
        custom_name = re.sub(r'[\\/*?:"<>|]', "", custom_name)
        quality = self.quality_combo.get().replace("p", "")
        mode = self.download_mode.get()

        # Tên file output
        output_template = os.path.join(self.save_path, f"{custom_name if custom_name else '%(title)s'}.%(ext)s")

        # Xây dựng command cho yt-dlp
        cmd = [
            self.ytdlp_path,
            url,
            '-o', output_template,
            '--ffmpeg-location', './ffmpeg.exe',
            '--no-warnings',
            '--newline'
        ]

        # Tự động tải toàn bộ playlist
        if "playlist" in url.lower() or "list=" in url:
            cmd.extend(['--yes-playlist'])
        
        # Cấu hình theo chế độ
        if mode == "audio":
            cmd.extend([
                '-f', 'bestaudio/best',
                '-x',
                '--audio-format', 'mp3',
                '--audio-quality', '192K'
            ])
            
            # Giữ file gốc .webm nếu được chọn
            if self.keep_original.get():
                cmd.append('--keep-video')
        else:
            cmd.extend([
                '-f', f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}][ext=mp4]/best',
                '--merge-output-format', 'mp4'
            ])

        try:
            self.status_label.configure(
                text=self.lang_manager.get_text("downloading", "Downloading:") + " 0%",
                text_color="yellow"
            )
            
            # Chạy yt-dlp
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Đọc output để cập nhật progress
            for line in process.stdout:
                line = line.strip()
                if '[download]' in line and '%' in line:
                    try:
                        # Extract percentage
                        percent_match = re.search(r'(\d+\.?\d*)%', line)
                        if percent_match:
                            percent_str = percent_match.group(1)
                            percent = float(percent_str) / 100
                            self.progress_bar.set(percent)
                            self.status_label.configure(
                                text=f"{self.lang_manager.get_text('downloading', 'Downloading:')} {percent_str}%",
                                text_color="yellow"
                            )
                    except Exception as e:
                        print(f"Parse progress error: {e}")
                elif 'Merging' in line or 'ExtractAudio' in line or 'Fixing' in line:
                    self.status_label.configure(
                        text=self.lang_manager.get_text("converting", "Converting format... Please wait!"),
                        text_color="orange"
                    )
            
            process.wait()
            
            if process.returncode == 0:
                self.status_label.configure(
                    text=self.lang_manager.get_text("success", "SUCCESS!"),
                    text_color="#2ecc71"
                )
                self.progress_bar.set(1)
                self.refresh_file_list()
            else:
                error_output = process.stderr.read() if process.stderr else ""
                self.status_label.configure(
                    text=self.lang_manager.get_text("error_download", "ERROR: Cannot download! Check link"),
                    text_color="#e74c3c"
                )
                print(f"Download error: {error_output}")
            
        except Exception as e:
            self.status_label.configure(
                text=f"ERROR: {str(e)[:50]}",
                text_color="#e74c3c"
            )
            print(f"Download exception: {e}")
        
        finally:
            self.btn_start.configure(state="normal")

    def on_closing(self):
        """Xử lý khi đóng ứng dụng"""
        self.music_player.stop()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()