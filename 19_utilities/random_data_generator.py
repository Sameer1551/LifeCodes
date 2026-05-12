#!/usr/bin/env python3
"""
random_data_generator.py

Universal fake data generator for testing.
Supports multiple regions, locales, and custom data sources.
Outputs CSV, JSON, SQL, XML, or YAML.
Language-agnostic, region-agnostic, platform-agnostic.

Usage:
    python random_data_generator.py --rows 100 --format csv --out data.csv
    python random_data_generator.py --rows 50 --region eu --format json
    python random_data_generator.py --template config.json --locale ja_JP
    python random_data_generator.py --custom-data my_data.json
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class RegionalData:
    """Regional data for different locales."""
    
    DATA = {
        "us": {
            "first_names": ["James", "Emma", "Liam", "Olivia", "Noah", "Ava", "William", "Sophia", "Benjamin", "Isabella"],
            "last_names": ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"],
            "cities": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego"],
            "states": ["NY", "CA", "IL", "TX", "AZ", "PA", "TX", "CA"],
            "streets": ["Main St", "Oak Ave", "Maple Dr", "Cedar Ln", "Pine Rd", "Elm St", "Washington Blvd", "Park Ave"],
            "companies": ["Acme Corp", "Globex", "Initech", "Umbrella", "Stark Ind", "Wayne Ent", "Oscorp", "Cyberdyne"],
            "phone_format": "({area}) {exchange}-{number}",
            "email_domains": ["gmail.com", "yahoo.com", "outlook.com", "proton.me", "icloud.com", "fastmail.com"],
            "postal_code": "#####",
            "country": "United States",
        },
        "eu": {
            "first_names": ["Hans", "Greta", "Lars", "Elsa", "Sven", "Astrid", "Olaf", "Freya", "Bjorn", "Sigrid"],
            "last_names": ["Müller", "Schmidt", "Fischer", "Weber", "Wagner", "Becker", "Schulz", "Hoffmann", "Koch", "Richter"],
            "cities": ["Berlin", "Munich", "Hamburg", "Cologne", "Frankfurt", "Stuttgart", "Düsseldorf", "Dortmund"],
            "states": ["Berlin", "Bavaria", "Hamburg", "North Rhine-Westphalia", "Baden-Württemberg", "Hesse"],
            "streets": ["Hauptstraße", "Marktstraße", "Schlossallee", "Parkweg", "Gartenstraße", "Bahnhofstraße", "Rathausplatz"],
            "companies": ["GmbH Co", "AG Corp", "SE Group", "KG Ltd", "OHG Inc", "PartG mbH", "e.V. Org"],
            "phone_format": "+49 {area} {number}",
            "email_domains": ["gmail.de", "yahoo.de", "outlook.de", "web.de", "gmx.de", "posteo.de"],
            "postal_code": "#####",
            "country": "Germany",
        },
        "asia": {
            "first_names": ["Wei", "Mei", "Hiro", "Yuki", "Jin", "Sakura", "Kenji", "Aiko", "Takeshi", "Emi"],
            "last_names": ["Wang", "Li", "Zhang", "Liu", "Chen", "Yang", "Huang", "Zhao", "Wu", "Zhou"],
            "cities": ["Beijing", "Shanghai", "Tokyo", "Osaka", "Seoul", "Busan", "Bangkok", "Singapore"],
            "states": ["Beijing", "Shanghai", "Tokyo", "Osaka", "Seoul", "Busan", "Bangkok", "Singapore"],
            "streets": ["Main Street", "Central Avenue", "Park Road", "Garden Lane", "River Drive", "Mountain View"],
            "companies": ["Tech Corp", "Digital Ltd", "Smart Solutions", "Future Systems", "Global Tech", "Innovation Inc"],
            "phone_format": "+{country_code} {area} {number}",
            "email_domains": ["gmail.com", "yahoo.co.jp", "outlook.jp", "163.com", "qq.com", "naver.com"],
            "postal_code": "###-####",
            "country": "Asia",
        },
        "latam": {
            "first_names": ["Carlos", "Maria", "Juan", "Ana", "Luis", "Sofia", "Miguel", "Elena", "Diego", "Carmen"],
            "last_names": ["García", "Rodríguez", "González", "Hernández", "López", "Martínez", "Sánchez", "Pérez", "Fernández", "Gómez"],
            "cities": ["Mexico City", "Buenos Aires", "São Paulo", "Lima", "Bogotá", "Santiago", "Caracas", "Montevideo"],
            "states": ["CDMX", "Buenos Aires", "São Paulo", "Lima", "Bogotá", "Santiago", "Caracas", "Montevideo"],
            "streets": ["Avenida Principal", "Calle Central", "Boulevard Mayor", "Callejón Real", "Paseo Grande"],
            "companies": ["Empresa SA", "Corporación Ltda", "Grupo SAS", "Industrias SC", "Compañía AC"],
            "phone_format": "+{country_code} {area} {number}",
            "email_domains": ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "terra.com", "uol.com.br"],
            "postal_code": "#####-###",
            "country": "Latin America",
        },
    }
    
    KEYBOARD_LAYOUTS = {
        "qwerty": "qwertyuiopasdfghjklzxcvbnm",
        "azerty": "azertyuiopqsdfghjklmwxcvbn",
        "qwertz": "qwertzuiopasdfghjklýxcvbnm",
        "dvorak": "pyfgcrlaoeuidhtnsqjkxbmwvz",
    }


class DataGenerator:
    """Universal data generator with regional support."""
    
    def __init__(self, region: str = "us", locale: str = "en_US", custom_data: Optional[Dict] = None):
        self.region = region.lower()
        self.locale = locale
        self.custom_data = custom_data or {}
        self.data = self._load_data()
    
    def _load_data(self) -> Dict:
        base_data = RegionalData.DATA.get(self.region, RegionalData.DATA["us"]).copy()
        base_data.update(self.custom_data)
        return base_data
    
    def name(self) -> str:
        first = random.choice(self.data.get("first_names", ["John"]))
        last = random.choice(self.data.get("last_names", ["Doe"]))
        return f"{first} {last}"
    
    def first_name(self) -> str:
        return random.choice(self.data.get("first_names", ["John"]))
    
    def last_name(self) -> str:
        return random.choice(self.data.get("last_names", ["Doe"]))
    
    def email(self, name: Optional[str] = None) -> str:
        if not name:
            name = self.name()
        parts = name.lower().split()
        local = f"{parts[0]}.{parts[1]}{random.randint(1, 99)}"
        domain = random.choice(self.data.get("email_domains", ["example.com"]))
        return f"{local}@{domain}"
    
    def phone(self) -> str:
        phone_format = self.data.get("phone_format", "+1 ({area}) {exchange}-{number}")
        area = random.randint(200, 999)
        exchange = random.randint(200, 999)
        number = random.randint(1000, 9999)
        country_code = self.data.get("country_code", "1")
        return phone_format.format(
            area=area,
            exchange=exchange,
            number=number,
            country_code=country_code,
        )
    
    def address(self) -> str:
        number = random.randint(100, 9999)
        street = random.choice(self.data.get("streets", ["Main St"]))
        city = random.choice(self.data.get("cities", ["City"]))
        state = random.choice(self.data.get("states", ["ST"]))
        postal = self._generate_postal_code()
        return f"{number} {street}, {city}, {state} {postal}"
    
    def _generate_postal_code(self) -> str:
        pattern = self.data.get("postal_code", "#####")
        result = ""
        for char in pattern:
            if char == "#":
                result += str(random.randint(0, 9))
            elif char == "@":
                result += chr(random.randint(65, 90))
            else:
                result += char
        return result
    
    def company(self) -> str:
        return random.choice(self.data.get("companies", ["Company Inc"]))
    
    def uuid(self) -> str:
        return str(uuid.uuid4())
    
    def date(self, start_year: int = 2020, end_year: int = 2025) -> str:
        start = datetime(start_year, 1, 1)
        end = datetime(end_year, 12, 31)
        delta = end - start
        offset = timedelta(days=random.randint(0, delta.days))
        return (start + offset).strftime("%Y-%m-%d")
    
    def datetime_obj(self, start_year: int = 2020, end_year: int = 2025) -> datetime:
        start = datetime(start_year, 1, 1)
        end = datetime(end_year, 12, 31)
        delta = end - start
        offset = timedelta(
            days=random.randint(0, delta.days),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        return start + offset
    
    def int(self, min_val: int = 0, max_val: int = 100, **kwargs: Any) -> int:
        return random.randint(min_val, max_val)
    
    def float(self, min_val: float = 0.0, max_val: float = 1000.0, decimals: int = 2, **kwargs: Any) -> float:
        val = random.uniform(min_val, max_val)
        return round(val, decimals)
    
    def bool(self) -> bool:
        return random.choice([True, False])
    
    def text(self, min_words: int = 5, max_words: int = 20) -> str:
        words = ["lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing", "elit", "sed", "do",
                 "eiusmod", "tempor", "incididunt", "ut", "labore", "et", "dolore", "magna", "aliqua", "enim"]
        count = random.randint(min_words, max_words)
        return " ".join(random.choice(words) for _ in range(count))
    
    def url(self) -> str:
        domains = ["example.com", "test.org", "demo.net", "sample.io"]
        paths = ["", "/page", "/about", "/contact", "/products"]
        return f"https://{random.choice(domains)}{random.choice(paths)}"
    
    def ip(self, ipv6: bool = False) -> str:
        if ipv6:
            return ":".join(str(random.randint(0, 65535)) for _ in range(8))
        return ".".join(str(random.randint(0, 255)) for _ in range(4))
    
    def mac(self) -> str:
        return ":".join(f"{random.randint(0, 255):02x}" for _ in range(6))
    
    def color(self, format: str = "hex") -> str:
        if format == "hex":
            return f"#{random.randint(0, 0xFFFFFF):06x}"
        elif format == "rgb":
            return f"rgb({random.randint(0, 255)}, {random.randint(0, 255)}, {random.randint(0, 255)})"
        elif format == "name":
            colors = ["red", "green", "blue", "yellow", "orange", "purple", "pink", "brown", "black", "white"]
            return random.choice(colors)
        return "#000000"
    
    def latitude(self) -> float:
        return round(random.uniform(-90, 90), 6)
    
    def longitude(self) -> float:
        return round(random.uniform(-180, 180), 6)
    
    def coordinates(self) -> str:
        return f"{self.latitude()}, {self.longitude()}"


class FieldParser:
    """Parses field specifications."""
    
    @staticmethod
    def parse(spec: str) -> tuple[str, str, Dict[str, Any]]:
        """Parse 'name:type[min,max]' into (name, type, kwargs)."""
        if ":" in spec:
            name, rest = spec.split(":", 1)
            type_part = rest.split("[")[0]
            kwargs = {}
            
            if "[" in rest and "]" in rest:
                params = rest.split("[")[1].split("]")[0]
                if "," in params:
                    min_val, max_val = params.split(",")
                    kwargs["min_val"] = float(min_val)
                    kwargs["max_val"] = float(max_val)
                else:
                    kwargs["value"] = params
            
            return name, type_part, kwargs
        
        return spec, "text", {}
    
    @staticmethod
    def infer_fields(template: Dict) -> List[str]:
        """Infer field types from template values."""
        fields = []
        for key, val in template.items():
            if isinstance(val, bool):
                fields.append(f"{key}:bool")
            elif isinstance(val, int):
                fields.append(f"{key}:int")
            elif isinstance(val, float):
                fields.append(f"{key}:float")
            elif isinstance(val, str):
                if "@" in val:
                    fields.append(f"{key}:email")
                elif re.match(r"^\d{3}-\d{3}-\d{4}$", val):
                    fields.append(f"{key}:phone")
                elif re.match(r"^\d{4}-\d{2}-\d{2}$", val):
                    fields.append(f"{key}:date")
                else:
                    fields.append(f"{key}:text")
            else:
                fields.append(key)
        return fields


class OutputWriter:
    """Writes generated data in various formats."""
    
    @staticmethod
    def write_csv(rows: List[Dict], out: Path) -> None:
        if not rows:
            return
        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    
    @staticmethod
    def write_json(rows: List[Dict], out: Path) -> None:
        with out.open("w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, default=str)
    
    @staticmethod
    def write_sql(rows: List[Dict], out: Path, table: str = "data") -> None:
        if not rows:
            return
        cols = list(rows[0].keys())
        lines = [f"INSERT INTO {table} ({', '.join(cols)}) VALUES"]
        for row in rows:
            vals = []
            for v in row.values():
                if v is None:
                    vals.append("NULL")
                elif isinstance(v, bool):
                    vals.append("1" if v else "0")
                elif isinstance(v, (int, float)):
                    vals.append(str(v))
                else:
                    vals.append(f"'{str(v).replace(chr(39), chr(39)*2)}'")
            lines.append(f"  ({', '.join(vals)}),")
        lines[-1] = lines[-1].rstrip(",") + ";"
        out.write_text("\n".join(lines), encoding="utf-8")
    
    @staticmethod
    def write_xml(rows: List[Dict], out: Path, root: str = "data") -> None:
        lines = [f'<?xml version="1.0" encoding="UTF-8"?>', f'<{root}>']
        for i, row in enumerate(rows):
            lines.append(f'  <row id="{i}">')
            for key, val in row.items():
                escaped = str(val).replace("&", "&").replace("<", "<").replace(">", ">")
                lines.append(f'    <{key}>{escaped}</{key}>')
            lines.append("  </row>")
        lines.append(f"</{root}>")
        out.write_text("\n".join(lines), encoding="utf-8")
    
    @staticmethod
    def write_yaml(rows: List[Dict], out: Path) -> None:
        try:
            import yaml
            with out.open("w", encoding="utf-8") as f:
                yaml.dump(rows, f, default_flow_style=False, allow_unicode=True)
        except ImportError:
            out.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")


def generate_data(
    rows: int,
    fields: List[str],
    generator: DataGenerator,
) -> List[Dict]:
    """Generate data rows."""
    type_map = {
        "name": generator.name,
        "first_name": generator.first_name,
        "last_name": generator.last_name,
        "email": generator.email,
        "phone": generator.phone,
        "address": generator.address,
        "company": generator.company,
        "uuid": generator.uuid,
        "date": generator.date,
        "datetime": lambda: generator.datetime_obj().isoformat(),
        "int": generator.int,
        "float": generator.float,
        "bool": generator.bool,
        "text": generator.text,
        "url": generator.url,
        "ip": generator.ip,
        "ipv6": lambda: generator.ip(ipv6=True),
        "mac": generator.mac,
        "color": generator.color,
        "latitude": generator.latitude,
        "longitude": generator.longitude,
        "coordinates": generator.coordinates,
    }
    
    results = []
    for _ in range(rows):
        row: Dict[str, Any] = {}
        for spec in fields:
            name, ftype, kwargs = FieldParser.parse(spec)
            gen_func = type_map.get(ftype, generator.text)
            row[name] = gen_func(**kwargs)
        results.append(row)
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Universal Random Data Generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--rows", type=int, default=10, help="Number of rows")
    parser.add_argument("--format", choices=["csv", "json", "sql", "xml", "yaml"], default="json", help="Output format")
    parser.add_argument("--out", help="Output file path")
    parser.add_argument("--fields", help="Comma-separated field specs (name:type[min,max])")
    parser.add_argument("--template", help="JSON template file to infer fields from")
    parser.add_argument("--table", default="data", help="SQL/XML table/root name")
    parser.add_argument("--region", choices=["us", "eu", "asia", "latam"], default="us", help="Regional data")
    parser.add_argument("--locale", default="en_US", help="Locale code")
    parser.add_argument("--custom-data", help="Custom data JSON file")
    parser.add_argument("--seed", type=int, help="Random seed")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    custom_data = None
    if args.custom_data:
        custom_data = json.loads(Path(args.custom_data).read_text(encoding="utf-8"))

    generator = DataGenerator(region=args.region, locale=args.locale, custom_data=custom_data)

    if args.template:
        tmpl = json.loads(Path(args.template).read_text(encoding="utf-8"))
        fields = FieldParser.infer_fields(tmpl)
    elif args.fields:
        fields = args.fields.split(",")
    else:
        fields = ["name", "email", "phone", "address", "company", "created_at:date", "active:bool"]

    rows = generate_data(args.rows, fields, generator)

    if args.out:
        out = Path(args.out)
        writers = {
            "csv": OutputWriter.write_csv,
            "json": OutputWriter.write_json,
            "sql": OutputWriter.write_sql,
            "xml": OutputWriter.write_xml,
            "yaml": OutputWriter.write_yaml,
        }
        writers[args.format](rows, out, table=args.table)
        print(f"Wrote {len(rows)} rows to {args.out}")
    else:
        print(json.dumps(rows, indent=2, default=str))


if __name__ == "__main__":
    main()
