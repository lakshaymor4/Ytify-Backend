from ytmusicapi import YTMusic
import os

import json
import os
import re

def setup(session_id: str, header_raw):
    try:
       
        headers = parse_raw_headers(header_raw)
        
        required_headers = ['cookie', 'user-agent', 'x-goog-authuser']
        missing_headers = []
        
        for header in required_headers:
            if header not in headers:
                missing_headers.append(header)
        
        if missing_headers:
            return {
                "success": False,
                "message": f"The following entries are missing in your headers: {', '.join(missing_headers)}. Please try a different request (such as /browse) and make sure you are logged in."
            }
        
        yt_headers = {
            "User-Agent": headers.get('user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0'),
            "Accept": headers.get('accept', '*/*'),
            "Accept-Language": headers.get('accept-language', 'en-US,en;q=0.5'),
            "Content-Type": headers.get('content-type', 'application/json'),
            "X-Goog-AuthUser": headers.get('x-goog-authuser', '0'),
            "x-origin": headers.get('x-origin', 'https://music.youtube.com'),
            "Cookie": headers['cookie']
        }
        
       
        print("Created header structure:")
        print(json.dumps(yt_headers, indent=2))
        base_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(base_dir, f"header{session_id}.json")
        with open(filepath, 'w') as f:
            json.dump(yt_headers, f, indent=2)
        
        if os.path.exists(filepath):
            print(f"{filepath} created successfully!")
            
            print("Testing authentication")
            try:
                
                ytmusic = YTMusic(filepath)
                
                playlists = ytmusic.get_library_playlists(limit=1)
                
                if playlists is not None:
                    print(f"Authentication test successful!")
                    print(f"Found library access (playlists: {len(playlists)})")
                    return {"success": True, "message": "Authentication successful and file created."}
                else:
                    print("Authentication works but no playlists found")
                    print("This is normal if you don't have any playlists")
                    return {"success": True, "message": "Authentication successful, but no playlists found."}
                    
            except Exception as test_error:
                print(f"File created but test failed: {test_error}")
                print("The file might still work for transfers")
                return {"success": True, "message": f"File created but authentication test failed: {test_error}"}
        else:
            return {"success": False, "message": "Header file was not created."}
            
    except Exception as e:
        print(f"Setup failed: {e}")
        return {"success": False, "message": f"Setup failed: {e}"}


def parse_raw_headers(header_raw):
    """Parse raw HTTP headers string into a dictionary"""
    headers = {}
    
    header_text = header_raw.strip()
    
    if header_text.startswith(('POST ', 'GET ', 'PUT ', 'DELETE ')):
        first_line_end = header_text.find('HTTP/')
        if first_line_end != -1:
            space_after_http = header_text.find(' ', first_line_end)
            if space_after_http != -1:
                header_text = header_text[space_after_http:].strip()
    
    import re
    
    header_pattern = r'(?=(?:Host|User-Agent|Accept|Accept-Language|Accept-Encoding|Content-Type|Content-Length|Referer|X-[\w-]+|Authorization|Connection|Cookie|Origin|Sec-[\w-]+|Priority|TE|Alt-Used|PREF|HSID|SSID|APISID|SAPISID|LOGIN_INFO|YSC|SIDCC|VISITOR_[\w_]+):)'
    
    parts = re.split(header_pattern, header_text)
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if ':' in part:
            colon_index = part.find(':')
            key = part[:colon_index].strip().lower()
            value = part[colon_index + 1:].strip()
            
            next_header_match = re.search(r'\s+(?:Host|User-Agent|Accept|Accept-Language|Accept-Encoding|Content-Type|Content-Length|Referer|X-[\w-]+|Authorization|Connection|Cookie|Origin|Sec-[\w-]+|Priority|TE|Alt-Used):', value)
            if next_header_match:
                value = value[:next_header_match.start()].strip()
            
            if key and value:
                headers[key] = value
    
    
    return headers
