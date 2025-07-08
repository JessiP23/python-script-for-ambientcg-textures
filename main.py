import os
import requests
import json
from urllib.parse import urlparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class PolyhavenDownloader:
    def __init__(self, base_dir="polyhaven_assets", max_workers=5):
        self.base_dir = base_dir
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Create base directory
        os.makedirs(base_dir, exist_ok=True)
        
        # Thread-safe counters
        self.lock = threading.Lock()
        self.downloaded_count = 0
        self.failed_count = 0
        
    def get_all_assets(self):
        """Get all available assets from Polyhaven API"""
        asset_types = ['textures', 'hdris', 'models']
        all_assets = {}
        
        for asset_type in asset_types:
            try:
                print(f"📡 Fetching {asset_type} from Polyhaven API...")
                url = f"https://api.polyhaven.com/assets?t={asset_type}"
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                assets = response.json()
                print(f"✅ Found {len(assets)} {asset_type}")
                all_assets[asset_type] = assets
                
            except Exception as e:
                print(f"❌ Failed to fetch {asset_type}: {e}")
                all_assets[asset_type] = {}
                
        return all_assets
    
    def get_asset_info(self, asset_id):
        """Get detailed information about a specific asset"""
        try:
            url = f"https://api.polyhaven.com/info/{asset_id}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Failed to get info for {asset_id}: {e}")
            return None
    
    def download_file(self, url, filepath, asset_name, file_type):
        """Download a single file with retry logic"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                print(f"⬇️ Downloading {asset_name} - {file_type} (attempt {attempt + 1})")
                
                response = self.session.get(url, timeout=60, stream=True)
                response.raise_for_status()
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                # Download with progress
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                
                # Verify file was downloaded
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    with self.lock:
                        self.downloaded_count += 1
                    print(f"✅ Downloaded {asset_name} - {file_type}")
                    return True
                else:
                    raise Exception("File is empty or doesn't exist")
                    
            except Exception as e:
                print(f"❌ Attempt {attempt + 1} failed for {asset_name} - {file_type}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    with self.lock:
                        self.failed_count += 1
                    return False
        
        return False
    
    def download_asset(self, asset_id, asset_type, preferred_resolution="2k"):
        """Download all files for a specific asset"""
        print(f"\n🎯 Processing {asset_type}: {asset_id}")
        
        # Get asset information
        asset_info = self.get_asset_info(asset_id)
        if not asset_info:
            return False
        
        # Create asset directory
        asset_dir = os.path.join(self.base_dir, asset_type, asset_id)
        os.makedirs(asset_dir, exist_ok=True)
        
        # Save metadata
        metadata_path = os.path.join(asset_dir, "metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(asset_info, f, indent=2)
        
        # Download files
        files_info = asset_info.get('files', {})
        downloaded_files = []
        
        for file_type, resolutions in files_info.items():
            if not isinstance(resolutions, dict):
                continue
                
            # Choose best available resolution
            available_resolutions = list(resolutions.keys())
            if not available_resolutions:
                continue
                
            # Prefer specified resolution, fallback to highest available
            resolution = preferred_resolution
            if resolution not in available_resolutions:
                # Sort resolutions by numeric value (e.g., 1k, 2k, 4k, 8k)
                try:
                    resolution = max(available_resolutions, 
                                   key=lambda x: int(x.replace('k', '000').replace('m', '000000')) if x.replace('k', '').replace('m', '').isdigit() else 0)
                except:
                    resolution = available_resolutions[0]
            
            file_info = resolutions.get(resolution, {})
            download_url = file_info.get('url')
            
            if download_url:
                # Generate filename
                parsed_url = urlparse(download_url)
                filename = os.path.basename(parsed_url.path)
                if not filename:
                    filename = f"{asset_id}_{file_type}_{resolution}.jpg"
                
                filepath = os.path.join(asset_dir, filename)
                
                # Skip if already downloaded
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    print(f"⏭️ Skipping {asset_id} - {file_type} (already exists)")
                    continue
                
                # Download file
                if self.download_file(download_url, filepath, asset_id, f"{file_type}_{resolution}"):
                    downloaded_files.append({
                        'type': file_type,
                        'resolution': resolution,
                        'path': filepath,
                        'url': download_url
                    })
        
        # Save download log
        if downloaded_files:
            download_log = os.path.join(asset_dir, "download_log.json")
            with open(download_log, 'w') as f:
                json.dump(downloaded_files, f, indent=2)
        
        return len(downloaded_files) > 0
    
    def download_all_assets(self, preferred_resolution="2k", asset_types=None):
        """Download all assets from Polyhaven"""
        if asset_types is None:
            asset_types = ['textures', 'hdris', 'models']
        
        print(f"🚀 Starting Polyhaven asset download...")
        print(f"📁 Download directory: {os.path.abspath(self.base_dir)}")
        print(f"🔧 Preferred resolution: {preferred_resolution}")
        print(f"⚡ Max workers: {self.max_workers}")
        
        # Get all assets
        all_assets = self.get_all_assets()
        
        # Create download tasks
        tasks = []
        for asset_type in asset_types:
            assets = all_assets.get(asset_type, {})
            for asset_id in assets:
                tasks.append((asset_id, asset_type, preferred_resolution))
        
        print(f"\n📊 Total assets to download: {len(tasks)}")
        
        # Download assets with threading
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {
                executor.submit(self.download_asset, asset_id, asset_type, preferred_resolution): (asset_id, asset_type)
                for asset_id, asset_type, preferred_resolution in tasks
            }
            
            completed = 0
            for future in as_completed(future_to_task):
                asset_id, asset_type = future_to_task[future]
                completed += 1
                
                try:
                    success = future.result()
                    status = "✅" if success else "❌"
                    print(f"{status} [{completed}/{len(tasks)}] {asset_type}: {asset_id}")
                except Exception as e:
                    print(f"❌ [{completed}/{len(tasks)}] Error processing {asset_type}: {asset_id} - {e}")
                    with self.lock:
                        self.failed_count += 1
        
        # Final summary
        print(f"\n🎉 Download Complete!")
        print(f"✅ Successfully downloaded: {self.downloaded_count} files")
        print(f"❌ Failed downloads: {self.failed_count} files")
        print(f"📁 Assets saved to: {os.path.abspath(self.base_dir)}")

def main():
    """Main function to run the downloader"""
    
    # Configuration
    BASE_DIR = "polyhaven_assets"  # Change this to your preferred directory
    PREFERRED_RESOLUTION = "2k"    # Options: 1k, 2k, 4k, 8k (depending on asset)
    MAX_WORKERS = 5               # Number of concurrent downloads
    ASSET_TYPES = ['textures', 'hdris', 'models']  # Which types to download
    
    # Create downloader instance
    downloader = PolyhavenDownloader(
        base_dir=BASE_DIR,
        max_workers=MAX_WORKERS
    )
    
    # Start download
    downloader.download_all_assets(
        preferred_resolution=PREFERRED_RESOLUTION,
        asset_types=ASSET_TYPES
    )

if __name__ == "__main__":
    main()