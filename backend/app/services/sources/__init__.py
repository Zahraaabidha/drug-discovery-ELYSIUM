"""Clients for external scientific databases (all public, no credentials required).

Credentials (all optional) are read from environment variables on the backend only:
  CONTACT_EMAIL       - sent in the User-Agent so providers can contact you (recommended)
  NCBI_API_KEY        - raises the PubChem rate limit (optional)
No secret is ever exposed to the frontend.
"""
