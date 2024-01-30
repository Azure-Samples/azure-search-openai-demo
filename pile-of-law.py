from datasets import load_dataset
import os

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

dataset = load_dataset("pile-of-law/pile-of-law", "eurlex")

id = 0

for entry in dataset["validation"]:
    id += 1

    if id % 20 == 0:
        break

    with open(f"temp/{id}.txt", "w", encoding="utf-8") as file:
        file.write(entry["text"])

    # if not os.path.exists("pile-of-law"):
    #     os.mkdir("pile-of-law")
    print(f"Nr {id}, Length {len(entry['text'])}")

    with open(f"data/{id}.pdf", "wb") as pdf_file:
        pdf = canvas.Canvas(pdf_file, pagesize=letter)

        with open(f"temp/{id}.txt", "r", encoding="utf-8") as file:
            lines = file.readlines()
            for line in lines:
                pdf.drawString(100, 800, line.strip())

        pdf.save()

    os.remove(f"temp/{id}.txt")
