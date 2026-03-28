#!/usr/bin/env python3
"""Invoice Extractor - Extract and organize invoices from ZIP archives."""

import argparse
import json
import re
import zipfile
from pathlib import Path
import PyPDF2

class InvoiceExtractor:
    def __init__(self, config=None):
        self.config = config or self._default_config()
        self.metadata = {}
        self.stats = {'total': 0, 'success': 0, 'incomplete': 0, 'errors': 0}

    @staticmethod
    def _default_config():
        return {
            'supplier_patterns': [
                r"(?:company|supplier|vendor|name)\s*[:\-]?\s*([A-Z][^\n]{3,80}?)(?:\n|$)",
            ],
            'date_patterns': [
                r"(?:date|issued|documento)\s*[:\-]?\s*(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})",
                r"(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{4})",
            ],
            'doc_number_patterns': [
                r"(?:number|invoice|reference|numero)\s*[:\-]?\s*([A-Z0-9/\-\.]+?)(?:\n|$)",
            ],
        }

    def extract_text_from_pdf(self, pdf_path, max_pages=3):
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for i in range(min(len(reader.pages), max_pages)):
                    text += reader.pages[i].extract_text()
                return text
        except:
            return ""

    def extract_supplier(self, text):
        for pattern in self.config['supplier_patterns']:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        return None

    def extract_date(self, text):
        for pattern in self.config['date_patterns']:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                date_str = match.group(1).strip()
                for sep in ['/', '-', '.']:
                    if sep in date_str:
                        parts = date_str.split(sep)
                        if len(parts) == 3:
                            try:
                                if len(parts[0]) == 4:
                                    year, month, day = parts
                                else:
                                    day, month, year = parts
                                return f"{year}-{int(month):02d}-{int(day):02d}"
                            except:
                                pass
        return None

    def extract_doc_number(self, text):
        for pattern in self.config['doc_number_patterns']:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip().replace('/', '-')
        return None

    def process_zip(self, zip_path, output_dir):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                pdf_files = [f for f in zf.namelist() if f.lower().endswith('.pdf')]
                self.stats['total'] = len(pdf_files)

                for i, pdf_name in enumerate(pdf_files, 1):
                    try:
                        with zf.open(pdf_name) as pdf_file:
                            temp_path = output_dir / pdf_name.split('/')[-1]
                            temp_path.write_bytes(pdf_file.read())

                        text = self.extract_text_from_pdf(temp_path)
                        supplier = self.extract_supplier(text) or 'Unknown'
                        date = self.extract_date(text)
                        doc_num = self.extract_doc_number(text)

                        supplier_folder = output_dir / supplier
                        supplier_folder.mkdir(exist_ok=True)

                        if date and doc_num:
                            yyyy, mm, dd = date.split('-')
                            new_name = f"{supplier.replace(' ', '_')}_{yyyy}_{mm}_{dd}_{doc_num}.pdf"
                            self.stats['success'] += 1
                        else:
                            new_name = f"{supplier.replace(' ', '_')}_unknown.pdf"
                            self.stats['incomplete'] += 1

                        new_path = supplier_folder / new_name
                        temp_path.rename(new_path)

                        rel_path = str(new_path.relative_to(output_dir))
                        self.metadata[rel_path] = {
                            'supplier': supplier,
                            'date': date or 'unknown',
                            'doc_number': doc_num or 'unknown'
                        }

                        if i % 100 == 0:
                            print(f"[{i}/{len(pdf_files)}] Processing...")

                    except Exception as e:
                        self.stats['errors'] += 1

            metadata_file = output_dir / 'metadata_final.json'
            with open(metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)

            return {'success': True, 'stats': self.stats}
        except Exception as e:
            return {'success': False, 'error': str(e)}

def main():
    parser = argparse.ArgumentParser(description='Extract and organize invoices')
    parser.add_argument('--zip-file', required=True, help='ZIP file path')
    parser.add_argument('--output-dir', required=True, help='Output directory')
    parser.add_argument('--config', help='Config JSON file')
    args = parser.parse_args()

    config = None
    if args.config:
        with open(args.config) as f:
            config = json.load(f)

    extractor = InvoiceExtractor(config)
    result = extractor.process_zip(args.zip_file, args.output_dir)

    if result['success']:
        print(f"✅ Complete! Success: {result['stats']['success']}, Incomplete: {result['stats']['incomplete']}")
    else:
        print(f"❌ Error: {result['error']}")

if __name__ == '__main__':
    main()
