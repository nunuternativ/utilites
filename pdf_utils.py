import os
import tempfile
from PyPDF2 import PdfFileMerger, PdfFileReader, PdfFileWriter
from reportlab.pdfgen import canvas

def overlay_all_pages(input_path, overlay_path, output_path, callback_func=None):
    '''
    args:
        input_path = source .pdf doc path
        overlay_path = overlay .png image path with transparency, 1:1 resolution
        output_path = path for result .pdf
    '''

    # make temp overlay pdf
    pdf_fh, pdf_tmp = tempfile.mkstemp(suffix='.pdf')
    os.close(pdf_fh)

    with open(input_path, "rb") as input_file:
        input_pdf = PdfFileReader(input_file)
        in_x, in_y, in_width, in_height = input_pdf.getPage(0).mediaBox  
        in_width, in_height = int(in_width), int(in_height)
        overlay_size = min((in_width, in_height))

        # put image on temp pdf
        c = canvas.Canvas(pdf_tmp, pagesize=(overlay_size, overlay_size))
        if in_height > in_width:
            x = 0
            y = abs(in_height-overlay_size) /2
        else:
            y = 0
            x = abs(in_width-overlay_size) /2
        c.drawImage(overlay_path, x, y, overlay_size, overlay_size, mask='auto')  
        c.save()

        with open(pdf_tmp, "rb") as overlay_file:
            overlay_reader = PdfFileReader(overlay_file)
            overlay_page = overlay_reader.getPage(0)

            # merge overlay pdf on every input pdf pages
            output = PdfFileWriter()
            numPages = input_pdf.getNumPages()
            for i in range(numPages):
                if callback_func:
                    callback_func((i+1, numPages))
                pdf_page = input_pdf.getPage(i)
                pdf_page.mergePage(overlay_page)
                output.addPage(pdf_page)

            # write out pdf
            with open(output_path, "wb") as merged_file:
                output.write(merged_file)

    # remove temp 
    os.remove(pdf_tmp)

    return output_path

'''

import sys
sys.path.append('D:/dev/core')
from PyPDF2 import PdfFileMerger, PdfFileReader, PdfFileWriter
from reportlab.pdfgen import canvas

import rf_config
from rf_utils.pipeline import watermark

src = r"D:\__playground\test_watermark_pdf\src1.pdf"
watermark_pdf = r"D:\__playground\test_watermark_pdf\watermark.pdf"
watermark_img = r"D:\__playground\test_watermark_pdf\watermark.png"
output = r"D:\__playground\test_watermark_pdf\output1.pdf"


c = canvas.Canvas(watermark_pdf) 
c.drawImage(watermark_img, 0,123, 595,595, mask='auto')  
c.save()

reload(watermark); watermark.add_watermark_pdf(src, watermark_pdf, output)

'''