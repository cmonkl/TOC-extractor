import fitz
import re
from ocr_toc_parsing import get_ocr_toc

def analyze_pages(doc):
    pages = {}
    # all candidate pages to have toc
    toc_candidates = []
    # scanned pages percent
    img_pages_frac = 0.0
    scanned = False
    
    for num, page in enumerate(doc.pages()):
        pages[num] = {}
        pages[num]['text'] = page.get_text()
        pages[num]['imgs'] = page.get_images()
        
        # check for number of words on a page and num of imgs
        pages[num]['is_img'] = len(re.findall(r'\w+', pages[num]['text'])) < 3 and len(pages[num]['imgs']) > 0
        if pages[num]['is_img']:
            img_pages_frac += 1

        # simple table of contents check
        if len(re.findall(r'[Сc]одержание|[Оо]главление', pages[num]['text'])) > 0:
            toc_candidates.append(num)
            
    # assume the docuemnt is scanned if more than 80% of pages are images
    img_pages_frac /= doc.page_count
    if img_pages_frac > 0.8:
        scanned = True
        
    return pages, toc_candidates, scanned

def get_toc(doc, pages, toc_page_num):
    toc = {}
    toc_regex = r'(\s[\d\.\(\)]*)([-—,\(\)0-9\w\s]+)([\.\s]{3,})(\d+)(?!\.)'
    
    # last page in toc
    last_num = -1

    # find toc on a few pages after toc_page_num
    # when toc takes more than one page
    for cur_page_num in range(toc_page_num, min(toc_page_num+15, doc.page_count)):
        text = pages[cur_page_num]['text']
        
        try:
            toc_end = re.search(r"[Оо]главление|[Сс]одержание", text).end()
        except:
            toc_end = 0

        len_prev = len(toc)
        toc, last_num = extend_toc(toc, text, toc_end, toc_regex, last_num)
        
        # toc ends when there is nothing to add
        if len(toc) == len_prev:
            break
    
    toc.pop('Оглавление', None)
    toc.pop('Содержание', None)
    
    if len(toc) > 3:
        return toc, cur_page_num
    else:
        return {}, None
    

def extend_toc(toc, text, toc_end, toc_regex, last_num):
    """Add to ToC"""
    
    # prepare text
    cleaned_text = text[toc_end:].replace('\n', " ")
    
    for match in re.finditer(toc_regex, cleaned_text):
        num, title, _, page_num = match.groups()
        
        # check for correctness
        if num and title and page_num and len(title.strip()) > 0 and len(page_num.strip())>0:
            page_num = int(page_num.strip())
            
            # page numbers should be in non-descending order
            if page_num >= last_num:
                title = num + " " + title.strip()
                toc[title.strip()] = page_num
                last_num = page_num
                
    return toc, last_num

def add_toc(doc, toc, toc_end_page):
    new_toc = []
    if toc_end_page + 1 > toc[list(toc.keys())[0]]:
        offset = toc_end_page
    else:
        offset = toc[list(toc.keys())[0]] - (toc_end_page + 1)

    for key in toc.keys():
        level = max(len(re.findall(r'(\d\.)', key)), 1)
        new_toc.append([level, key, toc[key]+offset])

    doc.set_toc(new_toc)
    
def extract_toc(file_path):
    with fitz.open(file_path) as doc:
        pages_info, toc_candidates, scanned = analyze_pages(doc)
        results = {'status':''}

        if not scanned:
            tocs = []
            for candidate_page_num in toc_candidates:
                candidate_toc, toc_page_end = get_toc(doc, pages_info, candidate_page_num)
                if len(candidate_toc) > 0:
                    tocs.append((candidate_toc, (candidate_page_num, toc_page_end)))
                    
            if len(tocs) == 1:
                file_toc, pages = tocs[0]
                toc_start_page, toc_end_page = pages 
                add_toc(doc, file_toc, toc_end_page)
                #doc.save(save_file_path)
                doc_bytes = doc.write()
                results['status'] = 'success'
                results['doc'] = doc_bytes
            elif len(tocs) > 1:
                results['status'] = 'multiple_tocs'
            else:
                results['status'] = 'toc_not_found'
        else:
            # find toc on second page of document
            ocr_toc = get_ocr_toc(doc)
            
            if ocr_toc:
                # assume toc is on the 2nd page
                toc_start_page = 1
                toc_end_page = 2
                add_toc(doc, ocr_toc, toc_end_page)
                doc_bytes = doc.write()
                results['status'] = 'success'
                results['doc'] = doc_bytes
            else:
                results['status'] = 'scanned_toc_not_found'

    return results

if __name__ == '__main__':
    response = extract_toc('/home/earina/fintech/FinTechProject/uploads/Промежуточная консолидированная отчетность за 6 мес 2023г.pdf')
    if response['status'] == 'success':
        with open("processed_result.pdf", "wb") as binary_file:
            binary_file.write(response['doc'])
    print(response['status'])