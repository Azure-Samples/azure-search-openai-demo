import PyPDF2


def extract_first_pages(input_pdf, output_pdf, num_pages=50):
    with open(input_pdf, "rb") as file:
        pdf_reader = PyPDF2.PdfReader(file)

        # Create a new PDF writer
        pdf_writer = PyPDF2.PdfWriter()

        # Extract and add the first 'num_pages' pages to the new PDF writer
        for page_num in range(min(len(pdf_reader.pages), num_pages)):
            page = pdf_reader.pages[page_num]
            pdf_writer.add_page(page)

        # Write the new PDF to the output file
        with open(output_pdf, "wb") as output_file:
            pdf_writer.write(output_file)


inputpdf = "codex2017.pdf"
outputpdf = "codex2017_short.pdf"
extract_first_pages(inputpdf, outputpdf, num_pages=50)
