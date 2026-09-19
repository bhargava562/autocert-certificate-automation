"""
Supabase Storage Template Provider & Cloud Storage Sink
Accesses Supabase Storage buckets via REST API using service role credentials.
"""

import json
import urllib.request
import urllib.parse
from typing import Optional
from ...core.config import Settings
from ..protocols import TemplateProvider, StorageSink

class SupabaseTemplateProvider:
    """Downloads templates from Supabase Storage 'templates' bucket"""

    def __init__(self, settings: Settings, bucket_name: str = "templates"):
        self.supabase_url = settings.supabase_url
        self.service_key = settings.supabase_service_key
        self.bucket_name = bucket_name

    def get_template_bytes(self, template_id: str) -> bytes:
        encoded_name = urllib.parse.quote(template_id)
        url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{encoded_name}"
        req = urllib.request.Request(url, headers={
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}"
        })
        with urllib.request.urlopen(req) as resp:
            return resp.read()

    def get_template_name(self, template_id: str) -> str:
        return template_id

class SupabaseStorageSink:
    """Uploads rendered certificates to Supabase Storage 'certificates' bucket"""

    def __init__(self, settings: Settings, bucket_name: str = "certificates"):
        self.supabase_url = settings.supabase_url
        self.service_key = settings.supabase_service_key
        self.bucket_name = bucket_name

    def save(self, content: bytes, filename: str, mime_type: str) -> str:
        encoded_name = urllib.parse.quote(filename)
        url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{encoded_name}"
        req = urllib.request.Request(
            url,
            data=content,
            headers={
                "apikey": self.service_key,
                "Authorization": f"Bearer {self.service_key}",
                "Content-Type": mime_type,
                "x-upsert": "true"
            },
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            resp.read()

        # Generate a signed URL valid for 24 hours
        sign_url = f"{self.supabase_url}/storage/v1/object/sign/{self.bucket_name}/{encoded_name}"
        sign_req = urllib.request.Request(
            sign_url,
            data=json.dumps({"expiresIn": 86400}).encode("utf-8"),
            headers={
                "apikey": self.service_key,
                "Authorization": f"Bearer {self.service_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(sign_req) as s_resp:
                res_data = json.loads(s_resp.read().decode("utf-8"))
                return f"{self.supabase_url}/storage/v1{res_data.get('signedURL')}"
        except Exception:
            return f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{encoded_name}"
