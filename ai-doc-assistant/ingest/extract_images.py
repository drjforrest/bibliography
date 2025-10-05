import fitz
from pathlib import Path


def extract_images(pdf_path, output_dir):
    """Extract images from PDF and save them to output directory."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    extracted_images = []

    for page_index in range(len(doc)):
        images = doc[page_index].get_images(full=True)
        for img_index, img in enumerate(images):
            xref = images[img_index][0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_filename = (
                output_dir
                / f"{Path(pdf_path).stem}_page_{page_index}_img_{img_index}.png"
            )

            with open(image_filename, "wb") as img_file:
                img_file.write(image_bytes)

            extracted_images.append(
                {
                    "file": str(image_filename),
                    "page": page_index + 1,
                    "source_pdf": pdf_path,
                }
            )

    doc.close()
    return extracted_images
