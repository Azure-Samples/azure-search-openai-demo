import sys
import os
import comtypes.client

# TODO : check if pdf already exists -> no need to recreate pdf
def wordToPDF(filepath):
    wdFormatPDF = 17
    if os.path.isfile(filepath):
        ext = os.path.splitext(filepath)
        outname = ext[0] + ".pdf"
        if ext[1] == ".docx" and not os.path.exists(outname):
            word = comtypes.client.CreateObject('Word.Application')
            doc = word.Documents.Open(filepath)
            doc.SaveAs(outname, FileFormat=wdFormatPDF)
            word.Quit()