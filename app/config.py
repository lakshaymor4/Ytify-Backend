import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
    SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:8000/callback/')
    SECRET = os.getenv('secret')
    REDIS_URL = os.getenv('REDIS')
    REDIS = os.getenv('REDIS_URL')
    YOUTUBE_MUSIC_HEADERS_FILE = "headers"
    
   
    CACHE_DIR = '.cache'
    SPOTIFY_CACHE_FILE = os.path.join(CACHE_DIR, 'spotify_cache.json')
    TRANSFER_LOG_FILE = 'transfer_log.txt'
    
    MAX_SEARCH_RESULTS = 5
    SIMILARITY_THRESHOLD = 0.8
    SIMILARITY_AI = 0.4
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SPOTIFY_CACHE_DIR = os.path.join(BASE_DIR, "spotify_caches")
    os.makedirs(SPOTIFY_CACHE_DIR, exist_ok=True)

    @classmethod
    def validate(cls):
        """Validate that all required configuration is present."""
        required_fields = [
            'SPOTIFY_CLIENT_ID',
            'SPOTIFY_CLIENT_SECRET'
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(cls, field):
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Missing required configuration: {', '.join(missing_fields)}")
        
        if not os.path.exists(cls.CACHE_DIR):
            os.makedirs(cls.CACHE_DIR)
