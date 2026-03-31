keri@2806-107e-001d-3309-767a-5a1f-87d4-f446:~/projects/Oracle_NBA$ PYTHONPATH=. uv run python3 scripts/init_v2_data.py
Traceback (most recent call last):
  File "/home/keri/projects/Oracle_NBA/scripts/init_v2_data.py", line 48, in <module>
    init_v2_infrastructure()
  File "/home/keri/projects/Oracle_NBA/scripts/init_v2_data.py", line 14, in init_v2_infrastructure
    client = bigquery.Client(project=project_id)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/keri/projects/Oracle_NBA/.venv/lib/python3.12/site-packages/google/cloud/bigquery/client.py", line 261, in __init__
    super(Client, self).__init__(
  File "/home/keri/projects/Oracle_NBA/.venv/lib/python3.12/site-packages/google/cloud/client/__init__.py", line 340, in __init__
    Client.__init__(
  File "/home/keri/projects/Oracle_NBA/.venv/lib/python3.12/site-packages/google/cloud/client/__init__.py", line 197, in __init__
    credentials, _ = google.auth.default(scopes=scopes)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/keri/projects/Oracle_NBA/.venv/lib/python3.12/site-packages/google/auth/_default.py", line 718, in default
    credentials, project_id = checker()
                              ^^^^^^^^^
  File "/home/keri/projects/Oracle_NBA/.venv/lib/python3.12/site-packages/google/auth/_default.py", line 711, in <lambda>
    lambda: _get_explicit_environ_credentials(quota_project_id=quota_project_id),
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/keri/projects/Oracle_NBA/.venv/lib/python3.12/site-packages/google/auth/_default.py", line 353, in _get_explicit_environ_credentials
    credentials, project_id = load_credentials_from_file(
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/keri/projects/Oracle_NBA/.venv/lib/python3.12/site-packages/google/auth/_default.py", line 179, in load_credentials_from_file
    raise exceptions.DefaultCredentialsError(
google.auth.exceptions.DefaultCredentialsError: File config/gcp-sa-key.json was not found.
keri@2806-107e-001d-3309-767a-5a1f-87d4-f446:~/projects/Oracle_NBA$ 
