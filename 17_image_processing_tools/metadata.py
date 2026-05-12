from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import os
import binascii

def get_exif_data(image_path):
    img = Image.open(image_path)
    exif_data = {}

    if hasattr(img, "_getexif") and img._getexif():
        for tag, value in img._getexif().items():
            decoded = TAGS.get(tag, f"Unknown_{tag}")
            exif_data[decoded] = value

    return exif_data


def extract_gps_info(exif_data):
    gps_info = {}
    if "GPSInfo" in exif_data:
        for key in exif_data["GPSInfo"]:
            decoded = GPSTAGS.get(key, key)
            gps_info[decoded] = exif_data["GPSInfo"][key]
    return gps_info


def check_unknown_tags(exif_data):
    unknown = {}
    for key in exif_data:
        if key.startswith("Unknown_"):
            unknown[key] = exif_data[key]
    return unknown


def check_appended_data(image_path):
    with open(image_path, "rb") as f:
        data = f.read()

    eof_marker = b'\xff\xd9'  # JPEG EOF
    eof_index = data.rfind(eof_marker)

    if eof_index != -1 and eof_index + 2 < len(data):
        extra = data[eof_index + 2:]
        return extra[:100]  # return first 100 bytes of hidden tail
    return None


def basic_lsb_steg_check(image_path):
    img = Image.open(image_path)
    pixels = list(img.getdata())

    lsb_bits = []

    for pixel in pixels[:1000]:  # sample first 1000 pixels
        if isinstance(pixel, int):
            lsb_bits.append(pixel & 1)
        else:
            for channel in pixel[:3]:
                lsb_bits.append(channel & 1)

    ones = sum(lsb_bits)
    zeros = len(lsb_bits) - ones

    return ones, zeros


def analyze_image(image_path):
    print(f"\n🔍 Analyzing: {image_path}\n")

    exif_data = get_exif_data(image_path)
    gps_info = extract_gps_info(exif_data)
    unknown_tags = check_unknown_tags(exif_data)
    appended_data = check_appended_data(image_path)
    lsb_stats = basic_lsb_steg_check(image_path)

    print("📷 EXIF DATA:")
    for k, v in exif_data.items():
        print(f"{k}: {v}")

    print("\n📍 GPS DATA:")
    if gps_info:
        for k, v in gps_info.items():
            print(f"{k}: {v}")
    else:
        print("No GPS data found")

    print("\n❓ UNKNOWN TAGS:")
    if unknown_tags:
        for k, v in unknown_tags.items():
            print(f"{k}: {v}")
    else:
        print("No unknown tags")

    print("\n📦 APPENDED DATA CHECK:")
    if appended_data:
        print("⚠️ Extra data found after image EOF!")
        print("Sample (hex):", binascii.hexlify(appended_data))
    else:
        print("No appended data detected")

    print("\n🧠 STEGANOGRAPHY (LSB) CHECK:")
    ones, zeros = lsb_stats
    print(f"LSB 1s: {ones}, 0s: {zeros}")
    if abs(ones - zeros) < len(lsb_stats) * 0.1:
        print("⚠️ Suspicious: Balanced LSB pattern (possible hidden data)")
    else:
        print("Likely normal image")



# 👉 RUN
analyze_image("D:\siddhesh\IMG_20220924_093316.jpg")