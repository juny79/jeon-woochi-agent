from PIL import Image, ImageDraw
import os
from pathlib import Path

def remove_background_v3(image_path, output_path):
    print(f"Processing {image_path} with v3...")
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size
    
    # 배경색 샘플링 (모서리)
    bg_color = img.getpixel((0, 0))
    
    datas = img.getdata()
    new_data = []
    
    for item in datas:
        r, g, b, a = item
        # 배경색과 유사하거나, 일정 수준 이상의 밝기(흰색계열)면 투명화
        dist = sum(abs(item[i] - bg_color[i]) for i in range(3))
        if dist < 100 or (r > 200 and g > 200 and b > 200):
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
            
    img.putdata(new_data)
    img.save(output_path, "PNG")
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    assets_dir = Path("assets")
    for img_name in ["jeon-woochi_b.png", "jeon-woochi_c.png"]:
        path = assets_dir / img_name
        if path.exists():
            remove_background_v3(path, path)
