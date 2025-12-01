# app/services/vector_store/fetcher.py
import httpx
import logging
from app.core.config import settings
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

headers = {
    "Authorization": f"Bearer {settings.LARAVEL_API_TOKEN}",
    "Accept": "application/json"
}

async def fetch_all_faqs() -> Dict[str, List[Dict[str, Any]]]:
    """Fetch FAQs dan return format asli API: {"data": [...]}"""
    url = f"{settings.LARAVEL_API_BASE_URL}/faqs"
    timeout = httpx.Timeout(settings.LARAVEL_API_TIMEOUT)
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers, params={"per_page": 1000})
            response.raise_for_status()
            data = response.json()
            logger.info(f"✅ Fetched {len(data.get('data', []))} FAQs")
            return data  # Return {"data": [...]}
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error fetching FAQs: {e}")
        return {"data": []}
    except httpx.RequestError as e:
        logger.error(f"❌ Request error fetching FAQs: {e}")
        return {"data": []}
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching FAQs: {e}")
        return {"data": []}


async def fetch_all_documents() -> Dict[str, List[Dict[str, Any]]]:
    """Fetch documents dan return format asli API: {"data": [...]}"""
    url = f"{settings.LARAVEL_API_BASE_URL}/documents"
    timeout = httpx.Timeout(settings.LARAVEL_API_TIMEOUT)
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            logger.info(f"✅ Fetched {len(data.get('data', []))} documents")
            return data  # Return {"data": [...]}
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error fetching documents: {e}")
        return {"data": []}
    except httpx.RequestError as e:
        logger.error(f"❌ Request error fetching documents: {e}")
        return {"data": []}
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching documents: {e}")
        return {"data": []}


async def fetch_tracking_status_from_api(tracking_number: str) -> Optional[Dict[str, Any]]:
    """Fetch tracking status by registration number."""
    url = f"{settings.LARAVEL_API_BASE_URL}/tracking/{tracking_number}"
    timeout = httpx.Timeout(settings.LARAVEL_API_TIMEOUT)
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            logger.info(f"✅ Tracking data for {tracking_number}")
            return data.get('data', data)
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error tracking {tracking_number}: {e}")
        return None
    except httpx.RequestError as e:
        logger.error(f"❌ Request error tracking {tracking_number}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error tracking {tracking_number}: {e}")
        return None


# Backward compatibility - keep old function names
fetch_faqs_from_api = fetch_all_faqs
fetch_documents_from_api = fetch_all_documents


if __name__ == "__main__":
    import asyncio
    
    async def test():
        faqs = await fetch_all_faqs()
        print("FAQs:", faqs)
        docs = await fetch_all_documents()
        print("Docs:", docs)
    
    asyncio.run(test())