import secrets
from pathlib import Path

destination = Path(__file__).with_name('.env')
if destination.exists():
    print('bi/.env already exists; existing credentials kept.')
else:
    password = secrets.token_urlsafe(18)
    destination.write_text(
        f'SUPERSET_SECRET_KEY={secrets.token_hex(48)}\nADMIN_PASSWORD={password}\n'
    )
    destination.chmod(0o600)
    print('Created bi/.env. Login: student. Password is in bi/.env.')
