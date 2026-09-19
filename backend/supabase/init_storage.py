#!/usr/bin/env python3
"""
Initialize Supabase Storage Buckets
Uses the SUPABASE_URL and SUPABASE_SERVICE_KEY from backend/.env to provision
the required storage buckets ('certificates' and 'templates') via REST API.
"""

import json
import os
import sys
import urllib.request
import urllib.error

def load_env(env_path: str) -> dict:
    env = {}
    if not os.path.exists(env_path):
        print(f"Error: .env file not found at {env_path}", file=sys.stderr)
        return env
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def create_bucket_if_not_exists(supabase_url: str, service_key: str, bucket_id: str, is_public: bool, max_size_bytes: int):
    endpoint = f"{supabase_url}/storage/v1/bucket"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json"
    }

    # 1. Check existing buckets
    req_list = urllib.request.Request(endpoint, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req_list) as resp:
            buckets = json.loads(resp.read().decode("utf-8"))
            existing_ids = [b.get("id") for b in buckets]
            if bucket_id in existing_ids:
                print(f"[OK] Bucket '{bucket_id}' already exists.")
                return
    except Exception as e:
        print(f"[WARN] Could not list buckets: {e}")

    # 2. Create bucket
    payload = {
        "id": bucket_id,
        "name": bucket_id,
        "public": is_public,
        "file_size_limit": max_size_bytes
    }
    req_create = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    try:
        with urllib.request.urlopen(req_create) as resp:
            if resp.status in (200, 201):
                print(f"[SUCCESS] Created bucket '{bucket_id}'.")
            else:
                print(f"[INFO] Bucket response status {resp.status}: {resp.read().decode('utf-8')}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        if "already exists" in body.lower() or e.code == 409:
            print(f"[OK] Bucket '{bucket_id}' already exists.")
        else:
            print(f"[ERROR] Failed to create bucket '{bucket_id}': HTTP {e.code} - {body}")
    except Exception as e:
        print(f"[ERROR] Exception creating bucket '{bucket_id}': {e}")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, "..", ".env")
    env = load_env(env_path)

    supabase_url = env.get("SUPABASE_URL")
    service_key = env.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not service_key:
        print("Error: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env", file=sys.stderr)
        sys.exit(1)

    print(f"Provisioning Supabase Storage buckets on: {supabase_url}...")
    # 'certificates': private, 10MB limit
    create_bucket_if_not_exists(supabase_url, service_key, "certificates", is_public=False, max_size_bytes=10485760)
    # 'templates': private, 25MB limit
    create_bucket_if_not_exists(supabase_url, service_key, "templates", is_public=False, max_size_bytes=26214400)
    print("Storage provisioning complete.")

if __name__ == "__main__":
    main()
