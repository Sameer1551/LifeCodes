# 1️⃣ Create a virtual environment (recommended)
python -m venv ~/envs/devtoolkit
source ~/envs/devtoolkit/bin/activate

# 2️⃣ Install the minimal dependencies
pip install PyPDF2 python-docx pillow tqdm pandas openpyxl
# Optional (OCR)
# pip install pytesseract

# 3️⃣ Place the two scripts somewhere on your PATH, e.g.
#    ~/bin/file_tools.py  and  ~/bin/data_tools.py
#    (Make them executable: chmod +x file_tools.py data_tools.py)
