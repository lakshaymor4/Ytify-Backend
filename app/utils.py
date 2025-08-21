import os
import json
from datetime import datetime
from config import Config

def log_message(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {level}: {message}"
    
    print(log_entry)
    
    try:
        with open(Config.TRANSFER_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    except Exception as e:
        print(f"Failed to write to log file: {e}")

def format_duration(duration_ms):
    if not duration_ms:
        return "0:00"
    
    total_seconds = duration_ms // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    
    return f"{minutes}:{seconds:02d}"

def sanitize_filename(filename):
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename.strip()

def create_backup_file(data, filename_prefix):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return filename
    except Exception as e:
        log_message(f"Failed to create backup file: {e}", "ERROR")
        return None

def load_json_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        log_message(f"File not found: {filepath}", "WARNING")
        return None
    except json.JSONDecodeError as e:
        log_message(f"Invalid JSON in file {filepath}: {e}", "ERROR")
        return None
    except Exception as e:
        log_message(f"Error loading file {filepath}: {e}", "ERROR")
        return None

def save_json_file(data, filepath):
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        log_message(f"Error saving file {filepath}: {e}", "ERROR")
        return False

def normalize_string(text):
    if not text:
        return ""
    
    text = text.lower().strip()
    
    replacements = {
        ' & ': ' and ',
        ' feat. ': ' featuring ',
        ' ft. ': ' featuring ',
        ' w/ ': ' with ',
        '(': '',
        ')': '',
        '[': '',
        ']': '',
        '"': '',
        "'": '',
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text

def validate_playlist_name(name):
    if not name or not name.strip():
        return False, "Playlist name cannot be empty"
    
    if len(name) > 150:
        return False, "Playlist name too long (max 150 characters)"
    
    sanitized_name = sanitize_filename(name)
    
    return True, sanitized_name

def estimate_transfer_time(num_tracks):
    estimated_seconds = num_tracks * 2.5
    
    if estimated_seconds < 60:
        return f"{int(estimated_seconds)} seconds"
    elif estimated_seconds < 3600:
        minutes = int(estimated_seconds / 60)
        return f"{minutes} minute(s)"
    else:
        hours = int(estimated_seconds / 3600)
        minutes = int((estimated_seconds % 3600) / 60)
        return f"{hours} hour(s) {minutes} minute(s)"

def get_file_size_mb(filepath):
    try:
        size_bytes = os.path.getsize(filepath)
        size_mb = size_bytes / (1024 * 1024)
        return round(size_mb, 2)
    except:
        return 0

def clean_cache_files():
    cache_dir = Config.CACHE_DIR
    if not os.path.exists(cache_dir):
        return
    
    try:
        for filename in os.listdir(cache_dir):
            filepath = os.path.join(cache_dir, filename)
            
            if os.path.isfile(filepath):
                file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(filepath))
                if file_age.days > 1:
                    os.remove(filepath)
                    log_message(f"Removed old cache file: {filename}")
    
    except Exception as e:
        log_message(f"Error cleaning cache files: {e}", "WARNING")
