import os
import time
import click

from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from marker.output import save_output



def ingest_bps_with_marker(converter, pdf_path, output_dir):
    rendered = converter(pdf_path)
    save_output(rendered, output_dir)


config = {
	"output_format": "markdown",
	"languages": "id,en",
	"disable_multiprocessing": True,
	"disable_tqdm": True,
}

converter = PdfConverter(
    artifact_dict=create_model_dict(),
    config=config,
)

input_pdf = "statistik_indonesia_2024.pdf"
output_folder = "./hasil_konversi"

markdown_file_path = ingest_bps_with_marker(converter, "data/pdf/0001-kompilasi-berita-resmi-statistik-provinsi-sulawesi-barat-semester-i-2025.pdf", "data/markdown")