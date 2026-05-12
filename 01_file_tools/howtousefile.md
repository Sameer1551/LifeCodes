# 1️⃣ Extract a single file
python file_tools.py extract mydoc.pdf out.txt

# 2️⃣ Bulk‑extract many PDFs (or any supported type)
python file_tools.py bulk-extract *.pdf -o extracted_texts --overwrite

# 3️⃣ Convert a DOCX to plain text
python file_tools.py convert report.docx report.txt

# 4️⃣ Convert many images to PDFs in one go
python file_tools.py bulk-convert *.png -s .pdf -o pdfs

# 5️⃣ Bulk‑rename files (adds a running index)
python file_tools.py rename ./photos "vacation_{index}{ext}" --dry-run

# 6️⃣ Organize a messy folder by extension
python file_tools.py organize ./downloads -c extension

# 7️⃣ Find duplicate files
python file_tools.py find-dupes ./datasets --algo sha256 --print

# 8️⃣ Zip a handful of CSVs together
python file_tools.py zip archive.zip data1.csv data2.csv

# 9️⃣ Compress an entire directory
python file_tools.py compress-dir -s ./logs -o logs_backup.zip -f zip

# 🔟 Extract an archive
python file_tools.py extract-archive mybackup.tar.gz -d ./restored




# all imports can be imported directly
from file_tools import bulk_rename, find_duplicates

renamed = bulk_rename(Path("./mydir"), "{index}_{name}{ext}")
dupes = find_duplicates(Path("./mydir"))

