from PIL import Image, ImageDraw
import os
from pathlib import Path

def flood_fill_remove_bg(image_path, output_path):
    print(f"Flood-filling {image_path}...")
    # 원본 이미지를 불러옵니다. (RGBA로 변환)
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size
    
    # 1. 배경색 샘플링 (구석 픽셀)
    bg_color = img.getpixel((0, 0))
    
    # 2. 마스크 생성 (배경과 비슷한 색을 찾기 위함)
    # 흰색/밝은 회색 배경이라고 가정하고 모서리부터 Flood Fill 시작
    # 내부의 흰색은 모서리와 연결되어 있지 않으므로 보호됩니다.
    
    # 임시로 L(8bit 그레이스케일) 마스크 생성
    mask = Image.new("L", (width + 2, height + 2), 0)
    
    # floodfill을 위해 이미지 복사
    temp_img = img.convert("RGB")
    
    # 색상 차이 허용 범위 (Tolerance)
    tolerance = 40 
    
    # 4개 모서리에서 각각 flood fill 실행하여 외곽 배경만 추출
    # 이 작업은 OpenCV가 더 강력하지만 PIL만으로 구현
    # PIL의 ImageDraw.floodfill은 특정 좌표부터 연결된 같은 색 영역을 칠함
    
    # 투명도가 이미 있는 경우(이전 작업으로 망가진 경우)를 대비해 RGB 기반으로 작업
    for seed in [(0, 0), (width-1, 0), (0, height-1), (width-1, height-1)]:
        target_color = temp_img.getpixel(seed)
        # 매우 밝은 색상일 때만 배경으로 간주하고 채움
        if sum(target_color) > 500: # R+G+B > 500 (밝은 색)
            ImageDraw.floodfill(img, seed, (255, 255, 255, 0), thresh=tolerance)

    img.save(output_path, "PNG")
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    assets_dir = Path("assets")
    # 원본 파일이 망가졌을 수 있으므로 사실 원본을 다시 받는게 좋지만
    # 일단 현재 파일에서 최대한 외곽만 다시 처리해봅니다.
    # 만약 캐릭터가 이미 투명해졌다면 이 코드는 의미가 없을 수 있습니다.
    # 유처에게 원본 이미지를assets 폴더에 다시 넣어달라고 안내해야 할 수 있습니다.
    if (assets_dir / "jeon-woochi_b.png").exists():
        flood_fill_remove_bg(assets_dir / "jeon-woochi_b.png", assets_dir / "jeon-woochi_b.png")
    if (assets_dir / "jeon-woochi_c.png").exists():
        flood_fill_remove_bg(assets_dir / "jeon-woochi_c.png", assets_dir / "jeon-woochi_c.png")
