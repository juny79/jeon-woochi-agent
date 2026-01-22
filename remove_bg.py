from PIL import Image
import os
from pathlib import Path

def remove_white_background(image_path, output_path):
    print(f"Processing {image_path}...")
    img = Image.open(image_path).convert("RGBA")
    
    # 투명한 배경으로 채울 새 이미지 생성
    new_img = Image.new("RGBA", img.size, (0, 0, 0, 0))
    
    datas = img.getdata()
    new_data = []
    
    # 배경색 샘플링 (구석 픽셀들이나 가장자리 평균)
    # 이미지의 0,0 픽셀을 기준으로 삼되, 흰색 계열이면 모두 처리
    for item in datas:
        r, g, b, a = item
        # 1. 거의 흰색에 가까운 색 (모든 채널이 200 이상이고 차이가 적은 경우)
        is_whitish = r > 200 and g > 200 and b > 200
        # 2. 혹은 R, G, B 값이 매우 균일하고 높은 경우 (회색 배경)
        is_grayish_white = abs(r-g) < 20 and abs(g-b) < 20 and abs(r-b) < 20 and r > 180
        
        if is_whitish or is_grayish_white:
            new_data.append((255, 255, 255, 0)) # 투명
        else:
            new_data.append(item)

    img.putdata(new_data)
    img.save(output_path, "PNG")
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    assets_dir = Path("assets")
    remove_white_background(assets_dir / "jeon-woochi_b.png", assets_dir / "jeon-woochi_b.png")
    # c.png도 처리할지 고민되지만, 일단 b.png가 가장 급함.
    # c.png는 유저가 "배경화면으로 변경"하라고 했으므로 배경처리를 해야할수도 있음.
    remove_white_background(assets_dir / "jeon-woochi_c.png", assets_dir / "jeon-woochi_c.png")
