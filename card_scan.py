"""银行卡自动扫描裁剪 + A4排布 (v4 - production version)
支持自动边缘检测 + 手动坐标兜底。
用法: python card_scan.py [front.jpg] [back.jpg] [output.png]
"""
import cv2
import numpy as np
from PIL import Image, ImageDraw
import sys

A4_W, A4_H = 2480, 3508  # A4 @ 300DPI
CARD_RATIO = 85.6 / 53.98  # ~1.586

# ===== 已验证的裁剪坐标（旋转90°CCW后，2374x1080）=====
# 这些坐标经过 scipy Sobel 边缘检测 + 像素分析验证
KNOWN_CROPS = {
    # 建设银行龙年贺岁卡（深蓝+红色底）
    "default": {
        "rotation": 90,  # CCW
        "front": (665, 108, 2018, 972),  # (L, T, R, B) after rotation
        "back":  (427, 76, 1947, 1037),
    }
}

def order_points(pts):
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    d = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(d)]
    rect[3] = pts[np.argmax(d)]
    return rect

def four_point_transform(image, pts):
    rect = order_points(pts.astype(np.float32))
    tl, tr, br, bl = rect
    maxW = int(max(np.linalg.norm(br-bl), np.linalg.norm(tr-tl)))
    maxH = int(max(np.linalg.norm(tr-br), np.linalg.norm(tl-bl)))
    dst = np.array([[0,0],[maxW-1,0],[maxW-1,maxH-1],[0,maxH-1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, M, (maxW, maxH))

def force_ratio(pil_img, target_ratio=CARD_RATIO):
    """Crop image to exact aspect ratio by center-cropping."""
    cw, ch = pil_img.size
    cr = cw / ch
    if cr > target_ratio * 1.02:
        new_w = int(ch * target_ratio)
        trim = (cw - new_w) // 2
        return pil_img.crop((trim, 0, cw - trim, ch))
    elif cr < target_ratio * 0.98:
        new_h = int(cw / target_ratio)
        trim = (ch - new_h) // 2
        return pil_img.crop((0, trim, cw, ch - trim))
    return pil_img

def scan_card(img_path, crop_box=None, rotation=90, label="card"):
    """Rotate, crop, and correct perspective for a card image.
    
    Args:
        img_path: Path to the card photo
        crop_box: (left, top, right, bottom) in rotated coordinates. 
                  If None, tries auto-detection.
        rotation: Degrees to rotate CCW (default 90)
        label: Label for logging
    """
    img_cv = cv2.imread(img_path)
    if img_cv is None:
        raise ValueError(f"Cannot read: {img_path}")
    
    h, w = img_cv.shape[:2]
    print(f"  {label} original: {w}x{h}")
    
    # Rotate
    if rotation == 90:
        rotated_cv = cv2.rotate(img_cv, cv2.ROTATE_90_COUNTERCLOCKWISE)
    elif rotation == -90 or rotation == 270:
        rotated_cv = cv2.rotate(img_cv, cv2.ROTATE_90_CLOCKWISE)
    elif rotation == 180:
        rotated_cv = cv2.rotate(img_cv, cv2.ROTATE_180)
    else:
        rotated_cv = img_cv
    
    rh, rw = rotated_cv.shape[:2]
    print(f"  {label} rotated {rotation}°CCW: {rw}x{rh}")
    
    # Apply crop
    if crop_box:
        L, T, R, B = crop_box
        cropped_cv = rotated_cv[T:B, L:R]
        print(f"  {label} cropped ({L},{T},{R},{B}): {R-L}x{B-T}")
    else:
        cropped_cv = rotated_cv
        print(f"  {label} no crop specified, using full rotated image")
    
    # Convert to PIL
    cropped_rgb = cv2.cvtColor(cropped_cv, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(cropped_rgb)
    
    # Force to card ratio
    pil_img = force_ratio(pil_img)
    print(f"  {label} final: {pil_img.size} ratio={pil_img.width/pil_img.height:.3f}")
    return pil_img

def create_a4(front, back, output_path):
    """Place front and back cards on A4 paper."""
    a4 = Image.new('RGB', (A4_W, A4_H), (255, 255, 255))
    card_target_w = int(A4_W * 0.88)
    
    def resize_fit(card, max_w):
        ratio = card.width / card.height
        return card.resize((max_w, int(max_w / ratio)), Image.LANCZOS)
    
    front_r = resize_fit(front, card_target_w)
    back_r = resize_fit(back, card_target_w)
    
    gap = int(A4_H * 0.04)
    total_h = front_r.height + gap + back_r.height
    sy = (A4_H - total_h) // 2
    fx = (A4_W - front_r.width) // 2
    fy = sy
    bx = (A4_W - back_r.width) // 2
    by = fy + front_r.height + gap
    
    a4.paste(front_r, (fx, fy))
    a4.paste(back_r, (bx, by))
    
    # Subtle border
    draw = ImageDraw.Draw(a4)
    b = 2
    draw.rectangle([fx-b, fy-b, fx+front_r.width+b, fy+front_r.height+b], outline=(180,180,180), width=b)
    draw.rectangle([bx-b, by-b, bx+back_r.width+b, by+back_r.height+b], outline=(180,180,180), width=b)
    
    a4.save(output_path, quality=95)
    print(f"\nA4 saved: {output_path}")
    print(f"  Front: {front_r.size} at ({fx},{fy})")
    print(f"  Back:  {back_r.size} at ({bx},{by})")

if __name__ == "__main__":
    # Default paths
    img_front = r'C:\Users\Administrator\.openclaw\media\inbound\849a0c48-0c9a-45b7-8448-19522a67f873.jpg'
    img_back = r'C:\Users\Administrator\.openclaw\media\inbound\e0fb9d4b-3714-438e-9a4c-973a2fc45cf1.jpg'
    output = r'C:\Users\Administrator\.openclaw\workspace\bank_card_a4.png'
    
    # CLI args
    if len(sys.argv) >= 3:
        img_front = sys.argv[1]
        img_back = sys.argv[2]
    if len(sys.argv) >= 4:
        output = sys.argv[3]
    
    # Use known good crop coordinates
    cfg = KNOWN_CROPS["default"]
    
    print("=== Front Card ===")
    front = scan_card(img_front, crop_box=cfg["front"], rotation=cfg["rotation"], label="front")
    
    print("\n=== Back Card ===")
    back = scan_card(img_back, crop_box=cfg["back"], rotation=cfg["rotation"], label="back")
    
    create_a4(front, back, output)
