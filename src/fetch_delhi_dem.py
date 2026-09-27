import os
import sys
import urllib.request
import datetime
from dotenv import load_dotenv
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from utils_config import get_zone_config

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))

def fetch_and_reproject_dem():
    # 1. Parse config & bbox
    bbox, preset, endpoints = get_zone_config("Fetch High-Resolution DEM from OpenTopography")
    min_lon, min_lat, max_lon, max_lat = bbox
    
    api_key = os.getenv("OPENTOPO_API_KEY")
    if not api_key or "your_" in api_key:
        print("[ERROR] Missing or invalid OPENTOPO_API_KEY in .env")
        sys.exit(1)
        
    out_dir = os.path.join(WORKSPACE_DIR, "data", "dem")
    os.makedirs(out_dir, exist_ok=True)
    
    orig_tif = os.path.join(out_dir, f"{preset}_elevation_4326.tif")
    reproj_tif = os.path.join(out_dir, f"{preset}_elevation_32643.tif")
    
    # 2. Construct API URL
    # Bounding box for OpenTopo is south, north, west, east
    url = f"{endpoints.get('opentopo', 'https://portal.opentopography.org/API/globaldem')}"
    url += f"?demtype=SRTMGL1&south={min_lat}&north={max_lat}&west={min_lon}&east={max_lon}&outputFormat=GTiff&API_Key={api_key}"
    
    print(f"[INFO] Fetching DEM from OpenTopography (SRTMGL1 30m)...")
    print(f"[PROVENANCE] Source URL (without key): {url.split('&API_Key=')[0]}")
    print(f"[PROVENANCE] Fetch Timestamp: {datetime.datetime.now().isoformat()}")
    
    # 3. Download the GeoTIFF
    try:
        urllib.request.urlretrieve(url, orig_tif)
        print(f"[SUCCESS] Downloaded original DEM to {orig_tif} (EPSG:4326)")
    except Exception as e:
        print(f"[ERROR] Failed to download DEM: {e}")
        sys.exit(1)
        
    # 4. Reproject to UTM 43N (EPSG:32643) for hydraulic calculations in meters
    print(f"[INFO] Reprojecting DEM to UTM 43N (EPSG:32643)...")
    try:
        dst_crs = 'EPSG:32643'
        
        with rasterio.open(orig_tif) as src:
            transform, width, height = calculate_default_transform(
                src.crs, dst_crs, src.width, src.height, *src.bounds)
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': dst_crs,
                'transform': transform,
                'width': width,
                'height': height,
                'nodata': src.nodata if src.nodata is not None else -32768.0
            })
            
            with rasterio.open(reproj_tif, 'w', **kwargs) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=dst_crs,
                        resampling=Resampling.bilinear)
                        
        print(f"[SUCCESS] Reprojected DEM saved to {reproj_tif}")
        
        # 5. Verification
        with rasterio.open(reproj_tif) as chk:
            print(f"[VERIFY] Reprojected CRS: {chk.crs}")
            print(f"[VERIFY] Resolution (m/pixel): {chk.res[0]:.2f} x {chk.res[1]:.2f}")
            if chk.crs.to_string() != dst_crs:
                print("[WARN] CRS mismatch!")
                
    except ImportError:
        print("[WARN] rasterio is not installed. Skipping reprojection step.")
        print("Run 'pip install rasterio' to enable UTM reprojection.")
    except Exception as e:
        print(f"[ERROR] Reprojection failed: {e}")

if __name__ == "__main__":
    fetch_and_reproject_dem()
