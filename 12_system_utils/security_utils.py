#!/usr/bin/env python3
"""
security_utils.py

A robust security toolkit for developers:

* `generate_password`   – Strong random password
* `generate_passphrase`– XKCD-style word passphrase (memorable)
* `check_strength`     – Estimate password entropy
* `hash_file`           – MD5 / SHA-* hash
* `encrypt_file`        – AES-256-GCM encryption with magic header
* `decrypt_file`        – Decryption with integrity check
* `secure_delete`      – Overwrite file with random data then delete

CLI Usage:
    python security_utils.py gen-pass 20
    python security_utils.py gen-phrase --words 4
    python security_utils.py encrypt secret.txt out.enc --password-env MY_PASS
    python security_utils.py hash file.txt --algo sha256
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import logging
import math
import os
import secrets
import string
import sys
from pathlib import Path
from typing import List, Tuple

log = logging.getLogger(__name__)

# Optional cryptography import
try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    AESGCM = None

# --- Wordlist for Passphrase (Subset of EFF Long Wordlist) ---
WORDLIST = [
    "correct", "horse", "battery", "staple", "apple", "brave", "cloud", "delta",
    "eagle", "focus", "giant", "hotel", "india", "juliet", "kilo", "lemon",
    "mike", "november", "oscar", "papa", "quebec", "romeo", "sierra", "tango",
    "uniform", "victor", "whiskey", "xray", "yankee", "zulu", "abstract", "boundary",
    "carbon", "digital", "energy", "future", "global", "horizon", "impact", "jungle"
    # Extend this list for production use
]

# --- Password & Passphrase ---

def generate_password(length: int = 16, upper: bool = True, digits: bool = True, symbols: bool = True) -> str:
    if length < 4:
        raise ValueError("Password length must be >= 4")
    
    alphabet = string.ascii_lowercase
    if upper: alphabet += string.ascii_uppercase
    if digits: alphabet += string.digits
    if symbols: alphabet += "!@#$%^&*"
    
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_passphrase(words: int = 4, sep: str = "-") -> str:
    """Generate a memorable passphrase (XKCD style)."""
    return sep.join(secrets.choice(WORDLIST) for _ in range(words))

def check_strength(password: str) -> Tuple[float, str]:
    """Estimate entropy and strength category."""
    # Rough entropy estimation: log2(charset_size^length)
    charset_size = 0
    if any(c.islower() for c in password): charset_size += 26
    if any(c.isupper() for c in password): charset_size += 26
    if any(c.isdigit() for c in password): charset_size += 10
    if any(c in "!@#$%^&*" for c in password): charset_size += 8
    
    entropy = math.log2(charset_size ** len(password)) if charset_size else 0
    
    if entropy < 28: rating = "Weak"
    elif entropy < 36: rating = "Fair"
    elif entropy < 60: rating = "Strong"
    else: rating = "Very Strong"
    
    return entropy, rating

# --- Hashing ---

def hash_file(path: Path, algo: str = "sha256", chunk_size: int = 8192) -> str:
    hasher = hashlib.new(algo)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

# --- Encryption (AES-256-GCM) ---

MAGIC_HEADER = b'SECUTIL_V01'

def _derive_key(password: str, salt: bytes) -> bytes:
    if AESGCM is None:
        raise ImportError("Please install 'cryptography' package.")
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100_000)
    return kdf.derive(password.encode())

def encrypt_file(input_path: Path, output_path: Path, password: str) -> None:
    if AESGCM is None: raise ImportError("Cryptography library required.")
    
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    
    data = input_path.read_bytes()
    ciphertext = aesgcm.encrypt(nonce, data, None)
    
    # Format: MAGIC + SALT + NONCE + CIPHERTEXT
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(MAGIC_HEADER + salt + nonce + ciphertext)
    log.info(f"Encrypted '{input_path}' -> '{output_path}'")

def decrypt_file(input_path: Path, output_path: Path, password: str) -> None:
    if AESGCM is None: raise ImportError("Cryptography library required.")
    
    blob = input_path.read_bytes()
    if not blob.startswith(MAGIC_HEADER):
        raise ValueError("Invalid file format or not encrypted with this tool.")
    
    # Parse components
    header_len = len(MAGIC_HEADER)
    salt = blob[header_len : header_len+16]
    nonce = blob[header_len+16 : header_len+16+12]
    ciphertext = blob[header_len+16+12:]
    
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(plaintext)
        log.info(f"Decrypted '{input_path}' -> '{output_path}'")
    except Exception as e:
        log.error("Decryption failed (wrong password or corrupted file)")
        raise ValueError("Decryption failed")

# --- Secure Delete ---

def secure_delete(path: Path, passes: int = 3) -> None:
    """Overwrite file with random data then delete."""
    if not path.is_file():
        raise FileNotFoundError(path)
    
    size = path.stat().st_size
    with path.open("r+b") as f:
        for _ in range(passes):
            f.seek(0)
            f.write(os.urandom(size))
            f.flush()
            os.fsync(f.fileno())
    os.remove(path)
    log.info(f"Securely deleted '{path}'")

# --- Token ---

def generate_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)

# --- CLI ---

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Security Utilities", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Password
    p_pass = sub.add_parser("gen-pass", help="Generate random password")
    p_pass.add_argument("length", type=int, nargs="?", default=16)
    p_pass.add_argument("--no-upper", action="store_true")
    p_pass.add_argument("--no-digits", action="store_true")
    p_pass.add_argument("--no-symbols", action="store_true")

    # Passphrase
    p_phrase = sub.add_parser("gen-phrase", help="Generate passphrase")
    p_phrase.add_argument("--words", type=int, default=4, help="Number of words")
    p_phrase.add_argument("--sep", default="-", help="Separator")

    # Hash
    p_hash = sub.add_parser("hash", help="Hash a file")
    p_hash.add_argument("file", type=Path)
    p_hash.add_argument("--algo", default="sha256")

    # Encrypt/Decrypt
    p_enc = sub.add_parser("encrypt", help="Encrypt a file")
    p_enc.add_argument("src", type=Path)
    p_enc.add_argument("dst", type=Path)
    p_enc.add_argument("--password", help="Password (use --password-env for safer input)")
    p_enc.add_argument("--password-env", help="Read password from environment variable")

    p_dec = sub.add_parser("decrypt", help="Decrypt a file")
    p_dec.add_argument("src", type=Path)
    p_dec.add_argument("dst", type=Path)
    p_dec.add_argument("--password", help="Password")
    p_dec.add_argument("--password-env", help="Read password from environment variable")

    # Secure Delete
    p_del = sub.add_parser("shred", help="Securely delete a file")
    p_del.add_argument("file", type=Path)

    # Strength
    p_str = sub.add_parser("strength", help="Check password strength")
    p_str.add_argument("password", help="Password to check")

    return parser

def _get_password(args) -> str:
    if args.password_env:
        pwd = os.environ.get(args.password_env)
        if not pwd: raise ValueError(f"Env var {args.password_env} not set")
        return pwd
    if args.password:
        return args.password
    return input("Enter password: ")

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _build_parser().parse_args()
    
    try:
        if args.cmd == "gen-pass":
            print(generate_password(args.length, upper=not args.no_upper, 
                                    digits=not args.no_digits, symbols=not args.no_symbols))
        
        elif args.cmd == "gen-phrase":
            print(generate_passphrase(args.words, args.sep))
        
        elif args.cmd == "strength":
            e, r = check_strength(args.password)
            print(f"Entropy: {e:.2f} bits\nRating: {r}")
        
        elif args.cmd == "hash":
            print(f"{args.algo.upper()}({args.file}) = {hash_file(args.file, args.algo)}")
        
        elif args.cmd == "encrypt":
            pwd = _get_password(args)
            encrypt_file(args.src, args.dst, pwd)
        
        elif args.cmd == "decrypt":
            pwd = _get_password(args)
            decrypt_file(args.src, args.dst, pwd)
        
        elif args.cmd == "shred":
            secure_delete(args.file)
            
    except Exception as e:
        log.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
