import re
import numpy as np
import cv2
import io
import fitz
import pytesseract
from PIL import Image

def preprocess(img):
    np_img = np.array(img)
    norm_img = np.zeros((img.size[1], img.size[0]))
    np_img = cv2.normalize(np_img, norm_img, 0, 255, cv2.NORM_MINMAX)
    gray_img = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)
    kernel_erosion = np.ones((3,3), np.uint8)
    erosion = cv2.erode(gray_img, kernel_erosion, iterations=1)
    kernel_dilation = np.ones((1,1), np.uint8)
    dilation = cv2.dilate(erosion, kernel_dilation, iterations=1)
    bin_img = cv2.threshold(dilation, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    res_img = cv2.medianBlur(bin_img, 3)
    return Image.fromarray(res_img)

def extract_from_line(line):
    # find page number
    num = re.findall(r'(\d+)$', line)
    has_num = len(num) > 0
    title_match = re.match( r'^([\s\d\.\(\)]*)([—а-яА-Я\s,():-]+)([+„,-за-яА-Я\s\.»\d]*)', line)

    # find text
    try:
        extracted_text =  "".join(title_match.groups()[:2])
        if has_num:
            extracted_text = extracted_text + " " + str(num[0])
    except:
        extracted_text = ""

    return extracted_text

def get_toc_from_scanned_text(text):
    toc = []
    toc_end = re.search(r"[Оо]главление|[Сс]одержание", text.lower()).end()
    cleaned_text = text[toc_end:]

    # store line with no digit at the end
    prev_line = ""
    for line in cleaned_text.split('\n'):
        extracted = extract_from_line(line)

        # pass empty line/ line with страница/line ending with :
        if extracted.strip() == "" or 'страница' in extracted.lower() or extracted[-1] == ':':
            if len(extracted) > 0 and extracted[-1] == ':':
                prev_line = ""
            continue
        
        # line ending with page number
        if extracted[-1].isdigit():
            # add prev line (without page num) content if extracted line does not start with number
            if prev_line != "" and not extracted[0].isdigit():
                toc.append(prev_line + " " + extracted)
                prev_line = ""
            else:
                # add only current line
                toc.append(extracted)
        # if line starts with digit it is a new paragraph
        elif extracted[0].isdigit():
            prev_line = extracted
        else:
            # concatenate lines that does not end with page number
            prev_line = prev_line + " " + extracted

    # create dict with page title and page number
    toc_dict = {}
    for toc_line in toc:
        # find page number
        num_matches = re.findall(r'(\d+)$', toc_line)

        if len(num_matches) > 0:
            title = re.sub(r'(\d+)$', '', toc_line).strip()
            num = num_matches[0]
            toc_dict[title] = int(num)

    return toc_dict

def get_ocr_toc(doc):
    # assume toc is located in second page
    page = doc.load_page(1)

    zoom = 1.2
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, dpi=300)
    img = Image.open(io.BytesIO(pix.tobytes()))
    preprocessed_img = preprocess(img)
    config='--psm 3'
    text = pytesseract.image_to_string(preprocessed_img, lang='rus', config=config)
    
    # find occurence of table of content word
    if len(re.findall(r"[Оо]главление|[Сс]одержание", text.lower())) > 0:
        toc = get_toc_from_scanned_text(text)
        return toc
    return None