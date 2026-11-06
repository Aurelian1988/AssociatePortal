"""Optional perspective correction for OCR; never replace the stored evidence."""
from PIL import Image, ImageOps


def scan_document(image, kind):
    if kind not in {'passport', 'licence_front', 'licence_back'}:
        return None
    try:
        import cv2
        import numpy as np
        source = ImageOps.exif_transpose(image).convert('RGB')
        source.thumbnail((3200, 3200))
        pixels = np.asarray(source)
        scale = min(1., 1200 / max(source.size))
        small = cv2.resize(pixels, None, fx=scale, fy=scale)
        gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 40, 120)
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        total = small.shape[0] * small.shape[1]
        for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:12]:
            if cv2.contourArea(contour) < total * .55:
                continue
            polygon = cv2.approxPolyDP(contour, .02 * cv2.arcLength(contour, True), True)
            if len(polygon) != 4 or not cv2.isContourConvex(polygon):
                continue
            points = polygon.reshape(4, 2).astype('float32') / scale
            sums, differences = points.sum(axis=1), np.diff(points, axis=1).ravel()
            quad = np.array([points[sums.argmin()], points[differences.argmin()], points[sums.argmax()], points[differences.argmax()]], dtype='float32')
            if len(np.unique(quad, axis=0)) != 4:
                continue
            tl, tr, br, bl = quad
            width = int(max(np.linalg.norm(tr-tl), np.linalg.norm(br-bl)))
            height = int(max(np.linalg.norm(bl-tl), np.linalg.norm(br-tr)))
            ratio = width / max(height, 1)
            low, high = (.58, .88) if kind == 'passport' else (1.4, 1.85)
            if not low <= ratio <= high or min(width, height) < 480:
                continue
            # Expand slightly to protect document borders and machine-readable text.
            centre = quad.mean(axis=0)
            quad = centre + (quad-centre)*1.025
            quad[:, 0] = np.clip(quad[:, 0], 0, source.width-1)
            quad[:, 1] = np.clip(quad[:, 1], 0, source.height-1)
            target = np.array([[0,0],[width-1,0],[width-1,height-1],[0,height-1]], dtype='float32')
            matrix = cv2.getPerspectiveTransform(quad, target)
            return Image.fromarray(cv2.warpPerspective(pixels, matrix, (width,height), flags=cv2.INTER_CUBIC))
    except Exception:
        # Unsupported processing or uncertain geometry must not block a photo.
        return None
    return None
