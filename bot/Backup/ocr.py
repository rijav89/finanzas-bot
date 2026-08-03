import pytesseract
import re
from PIL import Image
from config import TESSERACT_PATH

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


def leer_voucher(path):

    text = pytesseract.image_to_string(Image.open(path), lang="spa")

    text_limpio = text.replace("S5/", "S/").replace("S5", "S")

    monto_match = re.search(r"(\d{2,4}[.,]?\d{0,2})", text_limpio)

    if monto_match:
        monto = monto_match.group(1)
    else:
        monto = None

    if "yape" in text.lower():
        medio = "Yape"
    elif "plin" in text.lower():
        medio = "Plin"
    else:
        medio = "No identificado"

    return monto, medio