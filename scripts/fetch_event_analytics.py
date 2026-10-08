#!/usr/bin/env python3
import json, os, time
from pathlib import Path

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Filter, FilterExpression, Metric, RunReportRequest
)
from google.oauth2 import service_account

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"events-preview"/"admin"/"data"/"event-analytics.json"

PROPERTY_ID=os.getenv("GA4_PROPERTY_ID","").strip()
CREDS_JSON=os.getenv("GA4_SERVICE_ACCOUNT_JSON","").strip()

def run_range(client,start_date,end_date):
    request=RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        dimensions=[Dimension(name="itemId")],
        metrics=[Metric(name="eventCount")],
        date_ranges=[DateRange(start_date=start_date,end_date=end_date)],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="eventName",
                string_filter=Filter.StringFilter(value="view_item", match_type=Filter.StringFilter.MatchType.EXACT)
            )
        ),
        limit=100000,
    )
    res=client.run_report(request)
    out={}
    for row in res.rows:
        event_id=(row.dimension_values[0].value or "").strip()
        if not event_id:
            continue
        try: count=int(float(row.metric_values[0].value or 0))
        except: count=0
        out[event_id]=count
    return out

def main():
    if not PROPERTY_ID or not CREDS_JSON:
        raise SystemExit("Missing GA4_PROPERTY_ID or GA4_SERVICE_ACCOUNT_JSON")
    info=json.loads(CREDS_JSON)
    creds=service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/analytics.readonly"]
    )
    client=BetaAnalyticsDataClient(credentials=creds)
    data={
        "generated_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
        "property_id":PROPERTY_ID,
        "views_7d":run_range(client,"7daysAgo","today"),
        "views_30d":run_range(client,"30daysAgo","today"),
        "views_all":run_range(client,"2026-10-01","today"),
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("event analytics written", len(data["views_all"]))

if __name__=="__main__":
    main()
