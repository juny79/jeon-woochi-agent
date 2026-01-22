from PIL import Image, ImageDraw, ImageFilter
import os

def clean_background_v2(image_path):
    if not os.path.exists(image_path):
        print(f"File not found: {image_path}")
        return
    
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size
    
    # 1. 배경을 투명하게 만드는 Flood fill (4개 모서리)
    # thresh를 약간 높여서 잔상을 잡음
    mask = Image.new("L", (width, height), 0)
    
    # 임시로 배경을 채운 이미지 생성
    temp_img = img.copy()
    
    # 흰색 배경(255,255,255)을 투명하게 (0,0,0,0)으로
    target_color = (0, 0, 0, 0)
    
    # 모든 외곽 픽셀에 대해 floodfill 시도
    # (이미 배경이 투명한 경우가 있을 수 있으니 thresh 활용)
    for x in range(width):
        if temp_img.getpixel((x, 0))[:3] == (255, 255, 255):
            ImageDraw.floodfill(temp_img, (x, 0), target_color, thresh=50)
        if temp_img.getpixel((x, height-1))[:3] == (255, 255, 255):
            ImageDraw.floodfill(temp_img, (x, height-1), target_color, thresh=50)
            
    for y in range(height):
        if temp_img.getpixel((0, y))[:3] == (255, 255, 255):
            ImageDraw.floodfill(temp_img, (0, y), target_color, thresh=50)
        if temp_img.getpixel((width-1, y))[:3] == (255, 255, 255):
            ImageDraw.floodfill(temp_img, (width-1, y), target_color, thresh=50)

    # 2. 결과물 저장
    temp_img.save(image_path)
    print(f"Absolutely Cleaned: {image_path}")

if __name__ == "__main__":
    assets_dir = "assets"
    clean_background_v2(os.path.join(assets_dir, "jeon-woochi_b.png"))
    clean_background_v2(os.path.join(assets_dir, "jeon-woochi_c.png"))
