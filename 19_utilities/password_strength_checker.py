#!/usr/bin/env python3
"""
password_strength_checker.py

Universal password strength evaluator.
Supports multiple languages, keyboard layouts, and custom patterns.
Language-agnostic, platform-agnostic, locale-agnostic.

Usage:
    python password_strength_checker.py --password mysecret123
    python password_strength_checker.py --stdin
    python password_strength_checker.py --file passwords.txt
    python password_strength_checker.py --locale fr_FR --keyboard azerty
    python password_strength_checker.py --custom-patterns my_patterns.json
"""

from __future__ import annotations

import argparse
import json
import re
import string
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set


class KeyboardPatterns:
    """Keyboard patterns for different layouts."""
    
    PATTERNS = {
        "qwerty": {
            "rows": ["qwertyuiop", "asdfghjkl", "zxcvbnm"],
            "columns": ["qaz", "wsx", "edc", "rfv", "tgb", "yhn", "ujm", "ik,", "ol.", "p;/"],
            "adjacent": ["qw", "we", "er", "rt", "ty", "yu", "ui", "io", "op", "as", "sd", "df", "fg", "gh", "hj", "jk", "kl", "zx", "xc", "cv", "vb", "bn", "nm"],
            "repeats": ["aaa", "bbb", "ccc", "111", "222", "333"],
        },
        "azerty": {
            "rows": ["azertyuiop", "qsdfghjklm", "wxcvbn"],
            "columns": ["aqw", "zse", "xdr", "cft", "vgy", "bhu", "nj", "mk", "l", "p"],
            "adjacent": ["az", "ze", "er", "rt", "ty", "yu", "ui", "io", "op", "qs", "sd", "df", "fg", "gh", "hj", "jk", "kl", "wx", "xc", "cv", "vb", "bn"],
            "repeats": ["aaa", "bbb", "ccc", "111", "222", "333"],
        },
        "qwertz": {
            "rows": ["qwertzuiop", "asdfghjklý", "yxcvbnm"],
            "columns": ["qay", "wsx", "edc", "rfv", "tgb", "zhn", "ujm", "ik,", "ol.", "p"],
            "adjacent": ["qw", "we", "er", "rt", "ty", "yu", "ui", "io", "op", "as", "sd", "df", "fg", "gh", "hj", "jk", "kl", "yx", "xc", "cv", "vb", "bn"],
            "repeats": ["aaa", "bbb", "ccc", "111", "222", "333"],
        },
        "dvorak": {
            "rows": ["pyfgcrl", "aoeuidhtns", "qjkxbmwvz"],
            "columns": ["paq", "yoj", "fuk", "gix", "cxb", "rbm", "lwv", "e", "u", "d"],
            "adjacent": ["py", "yg", "gf", "fc", "cr", "rl", "ao", "oe", "eu", "ui", "id", "dt", "tn", "ns", "qj", "jk", "kx", "xb", "bm", "mw", "wv", "vz"],
            "repeats": ["aaa", "bbb", "ccc", "111", "222", "333"],
        },
    }
    
    @classmethod
    def get_patterns(cls, layout: str = "qwerty") -> Dict:
        return cls.PATTERNS.get(layout.lower(), cls.PATTERNS["qwerty"])


class CommonPasswords:
    """Common passwords by language/region."""
    
    PASSWORDS = {
        "en": {
            "password", "123456", "12345678", "qwerty", "abc123", "monkey", "1234567",
            "letmein", "trustno1", "dragon", "baseball", "iloveyou", "master",
            "sunshine", "ashley", "bailey", "shadow", "123123", "654321", "superman",
            "qazwsx", "michael", "football", "password1", "password123", "welcome", "welcome1",
        },
        "es": {
            "contraseña", "123456", "12345678", "hola", "amor", "casa", "dinero",
            "princesa", "dragon", "futbol", "bebe", "jesus", "maria", "carlos",
            "alexander", "matthew", "jordan", "andrew", "nicholas", "joshua",
        },
        "fr": {
            "motdepasse", "123456", "azerty", "bonjour", "amour", "maison", "argent",
            "princesse", "dragon", "football", "bebe", "jesus", "marie", "charles",
            "alexandre", "mathieu", "jordan", "andre", "nicolas", "joshua",
        },
        "de": {
            "passwort", "123456", "hallo", "liebe", "haus", "geld", "prinzessin",
            "drache", "fussball", "baby", "jesus", "maria", "karl", "alexander",
            "matthias", "jordan", "andreas", "niklas", "joshua",
        },
        "ja": {
            "パスワード", "123456", "こんにちは", "愛", "家", "お金", "姫",
            "ドラゴン", "サッカー", "赤ちゃん", "イエス", "マリア", "アレックス",
            "マシュー", "ジョーダン", "アンドリュー", "ニコラス", "ジョシュア",
        },
        "zh": {
            "密码", "123456", "你好", "爱", "家", "钱", "公主",
            "龙", "足球", "宝贝", "耶稣", "玛丽", "亚历山大",
            "马修", "乔丹", "安德鲁", "尼古拉斯", "约书亚",
        },
        "ru": {
            "пароль", "123456", "привет", "любовь", "дом", "деньги", "принцесса",
            "дракон", "футбол", "ребенок", "исус", "мария", "александр",
            "мэтью", "джордан", "андрей", "николай", "джошуа",
        },
        "ar": {
            "كلمةالمرور", "123456", "مرحبا", "حب", "بيت", "مال", "أميرة",
            "تنين", "كرةالقدم", "طفل", "يسوع", "مريم", "ألكسندر",
            "ماثيو", "جوردان", "أندرو", "نيكولاس", "جوشوا",
        },
    }
    
    @classmethod
    def get_passwords(cls, language: str = "en") -> Set[str]:
        return cls.PATTERNS.get(language.lower(), cls.PATTERNS["en"])


class PasswordAnalyzer:
    """Universal password strength analyzer."""
    
    def __init__(
        self,
        language: str = "en",
        keyboard_layout: str = "qwerty",
        custom_patterns: Optional[Dict] = None,
        custom_passwords: Optional[Set[str]] = None,
    ):
        self.language = language.lower()
        self.keyboard_layout = keyboard_layout.lower()
        self.custom_patterns = custom_patterns or {}
        self.custom_passwords = custom_passwords or set()
        
        self.keyboard_patterns = KeyboardPatterns.get_patterns(self.keyboard_layout)
        self.common_passwords = CommonPasswords.get_passwords(self.language)
        self.common_passwords.update(self.custom_passwords)
    
    def check_entropy(self, password: str) -> float:
        """Calculate password entropy."""
        pool_size = 0
        if any(c.islower() for c in password):
            pool_size += 26
        if any(c.isupper() for c in password):
            pool_size += 26
        if any(c.isdigit() for c in password):
            pool_size += 10
        if any(c in string.punctuation for c in password):
            pool_size += len(string.punctuation)
        if any(ord(c) > 127 for c in password):
            pool_size += 100  # Unicode characters
        
        if pool_size == 0:
            return 0.0
        return len(password) * (pool_size.bit_length() - 1)
    
    def check_keyboard_patterns(self, password: str) -> List[str]:
        """Check for keyboard patterns."""
        issues = []
        pw_lower = password.lower()
        
        patterns = self.keyboard_patterns
        
        for row in patterns.get("rows", []):
            if row in pw_lower or row[::-1] in pw_lower:
                issues.append(f"Keyboard row pattern: {row}")
        
        for col in patterns.get("columns", []):
            if col in pw_lower or col[::-1] in pw_lower:
                issues.append(f"Keyboard column pattern: {col}")
        
        for adj in patterns.get("adjacent", []):
            if adj in pw_lower or adj[::-1] in pw_lower:
                issues.append(f"Keyboard adjacent pattern: {adj}")
        
        for repeat in patterns.get("repeats", []):
            if repeat in pw_lower:
                issues.append(f"Repeated pattern: {repeat}")
        
        for custom_pattern in self.custom_patterns.get("keyboard", []):
            if custom_pattern.lower() in pw_lower:
                issues.append(f"Custom keyboard pattern: {custom_pattern}")
        
        return issues
    
    def check_repeated_chars(self, password: str) -> List[str]:
        """Check for repeated characters."""
        issues = []
        
        for i in range(len(password) - 2):
            if password[i] == password[i + 1] == password[i + 2]:
                issues.append(f"Repeated character: {password[i]}")
                break
        
        return issues
    
    def check_sequential_chars(self, password: str) -> List[str]:
        """Check for sequential characters."""
        issues = []
        pw_lower = password.lower()
        
        sequences = [
            "abcdefghijklmnopqrstuvwxyz",
            "zyxwvutsrqponmlkjihgfedcba",
            "0123456789",
            "9876543210",
        ]
        
        for seq in sequences:
            for i in range(len(seq) - 2):
                subseq = seq[i:i+3]
                if subseq in pw_lower:
                    issues.append(f"Sequential pattern: {subseq}")
                    break
        
        return issues
    
    def check_common_passwords(self, password: str) -> List[str]:
        """Check against common passwords."""
        issues = []
        pw_lower = password.lower()
        
        for common in self.common_passwords:
            if common.lower() in pw_lower:
                issues.append(f"Common password: {common}")
                break
        
        for custom in self.custom_passwords:
            if custom.lower() in pw_lower:
                issues.append(f"Custom common password: {custom}")
                break
        
        return issues
    
    def check_length(self, password: str) -> List[str]:
        """Check password length."""
        issues = []
        
        if len(password) < 8:
            issues.append("Too short (< 8 characters)")
        elif len(password) < 12:
            issues.append("Consider 12+ characters")
        
        return issues
    
    def check_character_classes(self, password: str) -> List[str]:
        """Check character class diversity."""
        issues = []
        
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in string.punctuation for c in password)
        has_unicode = any(ord(c) > 127 for c in password)
        
        char_classes = sum([has_lower, has_upper, has_digit, has_special, has_unicode])
        
        if not has_lower:
            issues.append("No lowercase letter")
        if not has_upper:
            issues.append("No uppercase letter")
        if not has_digit:
            issues.append("No digit")
        if not has_special and not has_unicode:
            issues.append("No special character")
        
        return issues, char_classes
    
    def analyze(self, password: str) -> Dict:
        """Comprehensive password analysis."""
        score = 10
        issues: List[str] = []
        feedback: List[str] = []
        
        # Length check
        length_issues = self.check_length(password)
        if length_issues:
            issues.extend(length_issues)
            score -= 2
        else:
            score += 1
        
        # Character classes
        class_issues, char_classes = self.check_character_classes(password)
        issues.extend(class_issues)
        score += char_classes - 2
        
        # Common passwords
        common_issues = self.check_common_passwords(password)
        if common_issues:
            issues.extend(common_issues)
            score = 0
        
        # Keyboard patterns
        keyboard_issues = self.check_keyboard_patterns(password)
        if keyboard_issues:
            issues.extend(keyboard_issues)
            score -= len(keyboard_issues)
        
        # Repeated characters
        repeat_issues = self.check_repeated_chars(password)
        if repeat_issues:
            issues.extend(repeat_issues)
            score -= 1
        
        # Sequential characters
        seq_issues = self.check_sequential_chars(password)
        if seq_issues:
            issues.extend(seq_issues)
            score -= 1
        
        # Entropy
        entropy = self.check_entropy(password)
        if entropy < 28:
            issues.append("Low entropy")
            score -= 2
        elif entropy > 60:
            score += 1
        
        # Normalize score
        score = max(0, min(10, score))
        
        # Determine strength
        if score >= 8:
            strength = "Strong"
        elif score >= 5:
            strength = "Medium"
        else:
            strength = "Weak"
        
        # Generate feedback
        if not any("lowercase" in i for i in issues):
            feedback.append("Good character diversity")
        if entropy > 60:
            feedback.append("High entropy")
        if len(password) >= 12:
            feedback.append("Good length")
        if not keyboard_issues:
            feedback.append("No keyboard patterns")
        
        return {
            "password": password,
            "score": score,
            "strength": strength,
            "entropy": round(entropy, 1),
            "length": len(password),
            "char_classes": char_classes,
            "issues": issues,
            "feedback": feedback,
            "language": self.language,
            "keyboard_layout": self.keyboard_layout,
        }


def load_custom_patterns(path: Path) -> Dict:
    """Load custom patterns from JSON file."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_custom_passwords(path: Path) -> Set[str]:
    """Load custom common passwords from file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return set(data)
        elif isinstance(data, dict) and "passwords" in data:
            return set(data["passwords"])
    except Exception:
        pass
    return set()


def main():
    parser = argparse.ArgumentParser(
        description="Universal Password Strength Checker",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--password", help="Password to check")
    parser.add_argument("--stdin", action="store_true", help="Read password from stdin")
    parser.add_argument("--file", help="Check passwords from file (one per line)")
    parser.add_argument("--locale", default="en", help="Language code (en, es, fr, de, ja, zh, ru, ar)")
    parser.add_argument("--keyboard", choices=["qwerty", "azerty", "qwertz", "dvorak"], default="qwerty", help="Keyboard layout")
    parser.add_argument("--custom-patterns", help="Custom patterns JSON file")
    parser.add_argument("--custom-passwords", help="Custom common passwords file")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    args = parser.parse_args()

    custom_patterns = None
    if args.custom_patterns:
        custom_patterns = load_custom_patterns(Path(args.custom_patterns))
    
    custom_passwords = None
    if args.custom_passwords:
        custom_passwords = load_custom_passwords(Path(args.custom_passwords))

    analyzer = PasswordAnalyzer(
        language=args.locale,
        keyboard_layout=args.keyboard,
        custom_patterns=custom_patterns,
        custom_passwords=custom_passwords,
    )

    passwords: List[tuple[str, Optional[str]]] = []

    if args.file:
        for line in Path(args.file).read_text(encoding="utf-8", errors="ignore").splitlines():
            passwords.append((line.strip(), None))
    elif args.stdin:
        pw = sys.stdin.read().strip()
        if pw:
            passwords.append((pw, None))
    elif args.password:
        passwords.append((args.password, None))
    else:
        try:
            import getpass
            pw = getpass.getpass("Enter password: ")
            passwords.append((pw, None))
        except Exception:
            print("Error: No password provided", file=sys.stderr)
            sys.exit(1)

    results = []
    for pw, label in passwords:
        result = analyzer.analyze(pw)
        results.append(result)

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        for result in results:
            display = result["password"][:2] + "*" * (len(result["password"]) - 2) if len(result["password"]) > 4 else "*" * len(result["password"])
            print(f"\nPassword: {display}")
            print(f"Strength: {result['strength']} (score: {result['score']}/10)")
            print(f"Entropy: {result['entropy']} bits")
            print(f"Length: {result['length']} chars, {result['char_classes']}/5 character classes")
            if result["issues"]:
                print(f"Issues: {', '.join(result['issues'])}")
            if result["feedback"]:
                print(f"Tips: {', '.join(result['feedback'])}")


if __name__ == "__main__":
    main()
