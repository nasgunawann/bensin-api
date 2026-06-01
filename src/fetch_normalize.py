#!/usr/bin/env python3
"""Fetch and normalize Pertamina price payload (local prototype).

This script reads `price.json` in the repository root, normalizes price fields,
and writes static JSON files under `v1/`:
 - v1/index.json
 - v1/nasional.json
 - v1/provinsi/{province_slug}.json

Designed as a local generator suitable to run in GitHub Actions.
"""
from __future__ import annotations
import json
import os
import sys

# Ensure repository root is in sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.config import (
    ROOT,
    PRICE_FILE,
    RAW_DIR,
    UPSTREAM_URL,
    OUT_DIR,
    PROV_DIR,
    PRODUCT_CANONICAL_MAP,
)
from src.schemas import ProvinceModel, IndexModel


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')


def slugify(text: str) -> str:
    s = text.lower().strip()
    s = s.replace('prov.', '').replace('provinsi', '')
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9\s-]", '', s)
    s = re.sub(r"\s+", '-', s)
    s = re.sub(r"-+", '-', s)
    s = s.strip('-')
    return s or 'unknown'


def parse_price(raw: Any) -> Tuple[Optional[int], str]:
    # Returns (price_rupiah_or_none, availability)
    if raw is None:
        return None, 'unavailable'
    s = str(raw).strip()
    if s == '' or s.lower() in ('n/a', 'na', 'null'):
        return None, 'unavailable'
    
    # remove currency prefixes
    s = re.sub(r'(?i)^\s*(rp|idr)\s*', '', s)
    s = s.strip()
    
    if not any(c.isdigit() for c in s):
        return None, 'unknown'
        
    has_dot = '.' in s
    has_comma = ',' in s
    
    if has_dot and has_comma:
        dot_idx = s.rfind('.')
        comma_idx = s.rfind(',')
        if dot_idx > comma_idx:
            thousands_sep = ','
            decimal_sep = '.'
        else:
            thousands_sep = '.'
            decimal_sep = ','
    elif has_dot:
        parts = s.split('.')
        if len(parts) > 2:
            thousands_sep = '.'
            decimal_sep = None
        else:
            last_part = parts[-1]
            if len(last_part) == 3:
                thousands_sep = '.'
                decimal_sep = None
            else:
                thousands_sep = None
                decimal_sep = '.'
    elif has_comma:
        parts = s.split(',')
        if len(parts) > 2:
            thousands_sep = ','
            decimal_sep = None
        else:
            last_part = parts[-1]
            if len(last_part) == 3:
                thousands_sep = ','
                decimal_sep = None
            else:
                thousands_sep = None
                decimal_sep = ','
    else:
        thousands_sep = None
        decimal_sep = None

    if thousands_sep:
        s = s.replace(thousands_sep, '')
        
    if decimal_sep:
        parts = s.split(decimal_sep)
        integer_part = re.sub(r'[^0-9]', '', parts[0])
        decimal_part = re.sub(r'[^0-9]', '', parts[1])
        if not integer_part:
            integer_part = '0'
        try:
            val_float = float(f"{integer_part}.{decimal_part}")
            val = int(val_float + 0.5)
        except ValueError:
            return None, 'unknown'
    else:
        digits = re.sub(r'[^0-9]', '', s)
        if digits == '':
            return None, 'unknown'
        try:
            val = int(digits)
        except ValueError:
            return None, 'unknown'

    if val == 0:
        return None, 'unavailable'
    return val, 'available'


def ensure_dirs() -> None:
    os.makedirs(PROV_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)


def build_province_file(prov_obj: Dict[str, Any]) -> Dict[str, Any]:
    province_name = prov_obj.get('province')
    slug = slugify(province_name)
    products = []
    
    pertamina_updated_at = None
    for p in prov_obj.get('list_price', []):
        updated = p.get('updatedDate')
        if updated:
            pertamina_updated_at = updated
            break

    for p in prov_obj.get('list_price', []):
        prod_name = p.get('product') or ''
        raw_price = p.get('price')
        updated = p.get('updatedDate')
        price_rupiah, availability = parse_price(raw_price)
        
        prod_clean = prod_name.strip().upper() if isinstance(prod_name, str) else None
        prod_canonical = PRODUCT_CANONICAL_MAP.get(prod_clean, prod_clean) if prod_clean else 'UNKNOWN'
        
        prod_item = {
            'product': prod_canonical,
            'price_rupiah': price_rupiah,
            'availability': availability,
        }
        
        if updated and updated != pertamina_updated_at:
            prod_item['pertamina_updated_at'] = updated
            
        products.append(prod_item)

    payload = {
        'province': province_name,
        'province_slug': slug,
        'pertamina_updated_at': pertamina_updated_at,
        'synced_at': iso_now(),
        'products': products,
    }
    return payload


def write_json(path: str, data: Any) -> None:
    try:
        # determine which model to use
        if path.endswith('index.json'):
            IndexModel.model_validate(data)
        elif '/provinsi/' in path.replace('\\', '/'):
            ProvinceModel.model_validate(data)
    except Exception as e:
        print('Validation error:', e)
        raise e
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--fetch', action='store_true', help='Fetch upstream data before normalizing')
    args = parser.parse_args()

    # If requested, try to fetch upstream and overwrite local PRICE_FILE
    if args.fetch:
        try:
            import httpx
            import time

            print('Fetching upstream:', UPSTREAM_URL)
            max_retries = 3
            backoff_factor = 2.0
            raw = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    with httpx.Client(timeout=15.0) as client:
                        resp = client.get(UPSTREAM_URL)
                        resp.raise_for_status()
                        raw = resp.text
                    break
                except Exception as exc:
                    print(f"Attempt {attempt} failed: {exc}")
                    if attempt == max_retries:
                        raise exc
                    sleep_time = backoff_factor ** attempt
                    print(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)

            ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
            os.makedirs(RAW_DIR, exist_ok=True)
            raw_path = os.path.join(RAW_DIR, f'raw-{ts}.json')
            try:
                with open(raw_path, 'w', encoding='utf-8') as f:
                    f.write(raw)
                # also update PRICE_FILE for downstream processing
                with open(PRICE_FILE, 'w', encoding='utf-8') as f:
                    f.write(raw)
                print('Saved raw payload to', raw_path)
            except OSError as oe:
                print('Failed writing raw file:', oe)
        except Exception as e:
            print('Warning: failed fetching upstream, will continue with existing price.json —', e)

    if not os.path.exists(PRICE_FILE):
        print('price.json not found at', PRICE_FILE)
        return
    ensure_dirs()
    with open(PRICE_FILE, 'r', encoding='utf-8') as f:
        src = json.load(f)

    # source may be wrapper with data array. Support several shapes:
    # 1) {"data": [ ... ]}
    # 2) {"data": {"data": [ ... ], "total":..}}
    if isinstance(src, dict):
        if 'data' in src and isinstance(src['data'], list):
            provinces = src['data']
        elif 'data' in src and isinstance(src['data'], dict) and 'data' in src['data'] and isinstance(src['data']['data'], list):
            provinces = src['data']['data']
        else:
            provinces = []
    elif isinstance(src, list):
        provinces = src
    else:
        provinces = []

    index = {
        'api_name': 'Indonesia Fuel Price API',
        'version': 'v1',
        'author': 'Nasrullah Gunawan',
        'github_repository': 'https://github.com/nasgunawann/bensin-api',
        'synced_at': iso_now(),
        'pertamina_updated_at': None,
        'provinsi_count': 0,
        'provinsi': {},
        'endpoints': {
            'all_provinces': '/v1/nasional.json',
        }
    }

    nasional_list = []
    for prov in provinces:
        if not isinstance(prov, dict):
            # skip unexpected entries
            print('Skipping non-object entry in data:', repr(prov))
            continue
        payload = build_province_file(prov)
        slug = payload['province_slug']
        prov_path = f'v1/provinsi/{slug}.json'
        out_path = os.path.join(ROOT, prov_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        write_json(out_path, payload)
        # compute metadata
        file_size = os.path.getsize(out_path)
        products_count = len(payload['products'])
        index['provinsi'][slug] = {
            'name': payload['province'],
            'slug': slug,
            'path': '/' + prov_path.replace('\\', '/'),
            'pertamina_updated_at': payload['pertamina_updated_at'],
            'synced_at': payload['synced_at'],
            'products_count': products_count,
            'file_size_bytes': file_size,
        }
        nasional_list.append(payload)
        # set global pertamina_updated_at if not set
        if index['pertamina_updated_at'] is None and payload['pertamina_updated_at']:
            index['pertamina_updated_at'] = payload['pertamina_updated_at']

    index['provinsi_count'] = len(index['provinsi'])

    # write nasional file
    nasional_payload = {
        'version': 'v1',
        'synced_at': index['synced_at'],
        'pertamina_updated_at': index['pertamina_updated_at'],
        'provinces': nasional_list,
    }
    write_json(os.path.join(ROOT, 'v1', 'nasional.json'), nasional_payload)

    # write index
    write_json(os.path.join(ROOT, 'v1', 'index.json'), index)

    print('Generated v1 files:')
    print(' - v1/index.json')
    print(' - v1/nasional.json')
    print(' - v1/provinsi/*.json')


if __name__ == '__main__':
    main()
