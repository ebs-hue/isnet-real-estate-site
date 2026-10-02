"""Prepare sanitized public datasets from connector-downloaded engine files.

No network or credentials are used here. Stage all required files first, validate,
then run the existing pricebook QA before committing the complete dataset batch.
"""
import argparse
import collections
import datetime as dt
import json
from pathlib import Path

MAPPING = {
    'yavne_public_beta.json': 'data/yavne/pricebook.json',
    'yavne_unique_inventory.json': 'data/yavne/inventory.json',
    'yavne_neighborhood_pricebooks.json': 'data/yavne/neighborhood-pricebooks.json',
    'yavne_neighborhoods.json': 'data/yavne/neighborhoods.json',
    'yavne_streets.json': 'data/yavne/streets.json',
    'yavne_address_index.json': 'data/yavne/address-index.json',
    'yavne_quarter_2026_Q3.json': 'data/yavne/quarter-2026-Q3.json',
    'karmi_gat_public_beta.json': 'data/pricebook.json',
    'karmi_gat_unique_inventory.json': 'data/karmi-gat-inventory.json',
    'karmi_gat_quarter_2026_Q3.json': 'data/karmi-gat-quarter-2026-Q3.json',
}
INVENTORY_FIELDS = ['neighborhood', 'street', 'house_number', 'rooms', 'area_sqm', 'floor',
                    'mamad', 'balcony', 'asking_price_ils', 'first_seen_at', 'last_seen_at', 'listing_kind']


def inventory(raw, city):
    if not isinstance(raw.get('rows'), list) or not raw['rows']:
        raise ValueError('Empty or invalid inventory: ' + city)
    return {'city': city, 'observed_at': max(str(r.get('last_seen_at') or '')[:10] for r in raw['rows']),
            'coverage': 'partial',
            'note': 'מודעות שנאספו; כפילויות מזוהות אוחדו. מועד תצפית אינו אישור שהדירה עדיין מוצעת למכירה.',
            'rows': [{k: r.get(k) for k in INVENTORY_FIELDS} for r in raw['rows']]}


def quarter(raw, city, address_index):
    result, seen, parcels = [], set(), {}
    for b in address_index.get('buildings', []):
        p = b.get('parcel', {})
        parcels.setdefault((str(p.get('gush')), str(p.get('helka'))), []).append(b)
    for item in raw.get('rows', []):
        if str(item.get('settlement', '')).strip().replace('קרית', 'קריית') != city:
            continue
        r = dict(item)
        date = dt.datetime.strptime(r['deal_date'], '%d/%m/%Y').date().isoformat()
        if not raw['period_from'] <= date <= raw['period_to']:
            continue
        r['_event_date_iso'] = date
        if city == 'יבנה':
            r.pop('_street', None)
            r.pop('_neighborhood', None)
        matches = parcels.get((str(int(r['gush'])), str(int(r['chelka']))), [])
        if len(matches) == 1:
            r['_street'], r['_neighborhood'] = matches[0]['street'], matches[0].get('neighborhood')
        r['_usable_standard_full_apartment'] = (
            r['deal_nature'] == 'דירה בבית קומות' and float(r['portion']) == 1
            and 20 <= float(r['asset_area']) <= 350 and 1 <= float(r['room_num']) <= 8
            and float(r['deal_amount']) > 0)
        identity = tuple(str(r.get(k)) for k in ['gush', 'chelka', 'sub_chelka', 'deal_amount', 'asset_area', 'room_num']) + (date,)
        if identity not in seen:
            seen.add(identity)
            result.append(r)
    out = dict(raw)
    out.update(rows=result, coverage_status='partial_reporting', representative_quarter=False,
               register_unique_count=len(result), raw_unique_count=len(result),
               standard_apartment_count=sum(r['_usable_standard_full_apartment'] for r in result),
               by_month=dict(sorted(collections.Counter(r['_event_date_iso'][:7] for r in result).items())))
    return out


def prepare(source, site, commit):
    # Read and validate the full batch before touching any destination.
    raw = {name: json.loads((source / name).read_text()) for name in MAPPING}
    batch = {}
    for name, destination in MAPPING.items():
        payload = raw[name]
        city = 'יבנה' if name.startswith('yavne') else 'קריית גת'
        if name.endswith('public_beta.json'):
            if payload.get('city') != city or not payload.get('rows'):
                raise ValueError('Invalid pricebook: ' + name)
        if name.endswith('unique_inventory.json'):
            payload = inventory(payload, city)
        if '_quarter_' in name:
            payload = quarter(payload, city, raw['yavne_address_index.json'] if city == 'יבנה' else {})
        batch[destination] = json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
    status = json.dumps({'engine_commit': commit,
        'method': 'authorized_github_connector', 'files': list(MAPPING.values()),
        'note': 'Source coverage remains partial; publication follows dataset QA.'}, indent=2) + '\n'
    changed = []
    for destination, content in batch.items():
        p = site / destination
        if not p.exists() or p.read_text() != content:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
            changed.append(destination)
    if changed:
        p = site / 'data/sync-status.json'
        p.write_text(status)
        changed.append('data/sync-status.json')
    return changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--site-dir', type=Path, required=True)
    parser.add_argument('--engine-commit', required=True)
    args = parser.parse_args()
    print(json.dumps({'changed': prepare(args.source_dir, args.site_dir, args.engine_commit)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
