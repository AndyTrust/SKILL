#!/bin/bash

# Example: Process ZIP of invoices

# Basic usage
python scripts/extract_and_organize.py \
  --zip-file invoices_march.zip \
  --output-dir ./invoices_organized

# With custom config
python scripts/extract_and_organize.py \
  --zip-file invoices_march.zip \
  --output-dir ./invoices_organized \
  --config assets/config_example.json
