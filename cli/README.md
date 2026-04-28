# Insighta CLI

Install globally:

```bash
pip install .
```

Then use:

```bash
insighta login --api-url http://localhost:8000
insighta whoami
insighta profiles list --gender male
insighta profiles search "young males from nigeria"
insighta profiles create --name "Harriet Tubman"
insighta profiles export --format csv
```

Credentials are stored at `~/.insighta/credentials.json`.
