from PIL import Image, ImageDraw
import os

def clean_background(image_path):
    if not os.path.exists(image_path):
        print(f"File not found: {image_path}")
        return
    
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size
    
    # 1. 배경 색상 추출 (모서리 샘플링)
    # 대부분의 경우 배경은 흰색 혹은 매우 밝은 색임
    bg_color = img.getpixel((0, 0))
    
    # 2. Flood fill을 모서리에서 시작하여 연결된 배경만 제거
    # Tolerance를 주어 흰색에 가까운 영역도 처리
    # (0,0), (width-1, 0), (0, height-1), (width-1, height-1) 에서 시작
    mask = Image.new("L", (width + 2, height + 2), 0)
    
    # 임시 이미지에 채우기 수행
    # PIL의 ImageDraw.floodfill 보다는 직접 픽셀 접근이 정확할 수 있음
    # 하지만 여기선 간단히 ImageDraw.floodfill 사용
    
    for x, y in [(0, 0), (width-1, 0), (0, height-1), (width-1, height-1)]:
        ImageDraw.floodfill(img, (x, y), (0, 0, 0, 0), thresh=30)
    
    # 3. 저장
    img.save(image_path)
    print(f"Done: {image_path}")

if __name__ == "__main__":
    assets_dir = "assets"
    clean_background(os.path.join(assets_dir, "jeon-woochi_b.png"))
    clean_background(os.path.join(assets_dir, "jeon-woochi_c.png"))
