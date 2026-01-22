from PIL import Image
import os
from pathlib import Path

def ultra_remove_bg(image_path):
    print(f"ULTRA Processing {image_path}...")
    img = Image.open(image_path).convert("RGBA")
    datas = img.getdata()
    
    new_data = []
    for item in datas:
        r, g, b, a = item
        # 배경 판정: 
        # 1. 아주 구석 색상과 비슷하거나 (R,G,B 합 차이가 120 미만)
        # 2. 모든 색상이 200 이상 (밝은 흰색/회색)
        # 3. 혹은 채도가 매우 낮은 밝은 색 (abs(r-g) < 15 and r > 180 etc)
        
        is_bright = r > 190 and g > 190 and b > 190
        is_neutral = abs(r-g) < 20 and abs(g-b) < 20 and abs(r-b) < 20 and r > 170
        
        if is_bright or is_neutral:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
            
    img.putdata(new_data)
    # 주변 투명 픽셀 제거 (Crop)
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
        
    img.save(image_path, "PNG")
    print(f"Saved {image_path}")

if __name__ == "__main__":
    assets_dir = Path("assets")
    ultra_remove_bg(assets_dir / "jeon-woochi_b.png")
    ultra_remove_bg(assets_dir / "jeon-woochi_c.png")
