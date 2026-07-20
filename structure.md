.
├── consignes
│   ├── 1_spec_fonctionnelles.md
│   ├── 2_cahiers_des_charges.md
│   └── 3_etat_avancement.md
├── data
│   ├── processed
│   │   ├── water_imputed.csv
│   │   └── water_std.csv
│   └── raw
│       └── water_potability.csv
├── docker-compose.yml
├── Dockerfile
├── docs
│   ├── archi.md
│   ├── archi.mmd
│   ├── data_model.md
│   ├── erDiagram.mmd
│   ├── flux_prediction.mmd
│   ├── incidents
│   │   ├── bugfix.md
│   │   ├── incident_a_faire.md
│   │   ├── incident_DNS_rebinding.md
│   │   ├── incident_ocr.md
│   │   ├── OCR_ko_front.png
│   │   └── OCR_ko_swagger.png
│   ├── pipeline_mlops.mmd
│   ├── RGPD.md
│   └── veille_OCR.md
├── front
│   ├── __pycache__
│   │   ├── analyste.cpython-312.pyc
│   │   ├── app.cpython-312.pyc
│   │   ├── auth.cpython-312.pyc
│   │   ├── client.cpython-312.pyc
│   │   └── exploitation.cpython-312.pyc
│   ├── analyste.py
│   ├── app.py
│   ├── auth.py
│   ├── client.py
│   ├── exploitation.py
│   ├── static
│   │   ├── css
│   │   │   └── main.css
│   │   └── img
│   │       └── eau.webp
│   └── templates
│       ├── analyste
│       │   └── dashboard.html
│       ├── base.html
│       ├── client
│       │   └── dashboard.html
│       ├── exploitation
│       │   └── dashboard.html
│       └── login.html
├── img
│   ├── archi_drink_safe.png
│   ├── flux_prediction.png
│   ├── pipeline_mlops.png
│   ├── pipeline_mlops.svg
│   └── routage.svg
├── mlruns_artifacts
│   └── 1
│       ├── 002df5ef164b41eb8d8ed83cbe9f3ea0
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 005da901ff504764a6da63329f20e634
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 07e19d0db88d421bb2cbf829c0538f39
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 136d398a03af48948b70be32a8c9fe2c
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 1827305120b240f4b3fc709a348fa4b4
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 23e7e862bbc94064be1fa442b4bf5499
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 273d00291c9548989015fa0d3b3cb7e2
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 311e964bd9e84455b4cecbc91bbcf3ab
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 31e1142f76314dda9a2e7143fd655bbe
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 3880ed836b514c5a868e98b0e1b0f89a
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 3946bab87e1d4c2db96ae81089224f76
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 4058639a4bd04432994492f43ec5b372
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 4a7f21d8da644a9cbf5156785d63dcfa
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 4eadd297a6db48c2b872990ff639a935
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 508805d9140e4712bf0c083f9e8fa485
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 50cd66095cb342b8b277b794adbb7f0d
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 611713ebf30c4d579b102b1b9664ada6
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 6bc08df94cd44d41895bd3a08d5275d8
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 78a7de00396247c886bef759591a5eb6
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 78e550c5674b43e38aaa26e59f426d61
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 845caee4e5db427f9cc8900185776c59
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 8be1c4669f9c485f9db05c2c98adbfed
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 960c739f26bb48679c1e5ba4b6ed9e9a
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── 9f2e433a3781445cb50fcd7d6cc5b757
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── a11fb4992eba4376b475544da833188a
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── ab8dc6da0824492bb0f44a93562f1044
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── adfbf35e885e447db3479c448d177d35
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── b037231ba1bc4dba8fd3f94cd8f4ad96
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── b08fdb4b20ff4ea4b01f6be06d5b1258
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── c24982b3566d4c24b5288d60108618fe
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── c35f0d954f304d0dbd81e383d18e232d
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── d08fff55a3d54337b972bfb447d888c1
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── d43008c9820a4c14921fed77a35a5e9a
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── d9ebeee6fd194e9f96ba9e90692e0f29
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       ├── daa3a6dd2b03424d966703e6194b88ed
│       │   └── artifacts
│       │       └── model
│       │           ├── conda.yaml
│       │           ├── metadata
│       │           │   ├── conda.yaml
│       │           │   ├── MLmodel
│       │           │   ├── python_env.yaml
│       │           │   └── requirements.txt
│       │           ├── MLmodel
│       │           ├── model.pkl
│       │           ├── python_env.yaml
│       │           └── requirements.txt
│       └── dae0baf667db47b3bf8611e77ce3b725
│           └── artifacts
│               └── model
│                   ├── conda.yaml
│                   ├── metadata
│                   │   ├── conda.yaml
│                   │   ├── MLmodel
│                   │   ├── python_env.yaml
│                   │   └── requirements.txt
│                   ├── MLmodel
│                   ├── model.pkl
│                   ├── python_env.yaml
│                   └── requirements.txt
├── monitoring
│   ├── dashboards
│   │   └── dashboard_red.json
│   ├── dashboards.yml
│   └── datasources.yml
├── notebooks
│   ├── __init__.py
│   └── eda.ipynb
├── prometheus.yml
├── pyproject.toml
├── README.md
├── scripts
│   ├── auth
│   │   ├── hash_admin_passwords.py
│   │   ├── migrate_keys_to_hash.py
│   │   └── seed_admins.py
│   └── dat_prep
│       ├── analysis_utils.py
│       └── cleaning_utils.py
├── src
│   ├── __pycache__
│   │   ├── api.cpython-312.pyc
│   │   └── config.cpython-312.pyc
│   ├── api.py
│   ├── config.py
│   ├── dependencies
│   │   ├── __pycache__
│   │   │   └── auth.cpython-312.pyc
│   │   └── auth.py
│   ├── experiment.py
│   ├── init_mlflow.py
│   ├── models.py
│   ├── routes
│   │   ├── __pycache__
│   │   │   ├── clients.cpython-312.pyc
│   │   │   ├── measurements.cpython-312.pyc
│   │   │   ├── monitoring.cpython-312.pyc
│   │   │   ├── ocr.cpython-312.pyc
│   │   │   └── predictions.cpython-312.pyc
│   │   ├── clients.py
│   │   ├── measurements.py
│   │   ├── monitoring.py
│   │   ├── ocr.py
│   │   └── predictions.py
│   └── waterflow.egg-info
│       ├── dependency_links.txt
│       ├── PKG-INFO
│       ├── requires.txt
│       ├── SOURCES.txt
│       └── top_level.txt
├── structure.md
├── tests
│   ├── test_functionnal.py
│   ├── test_non_regression.py
│   └── test_unit.py
└── uv.lock

177 directories, 410 files
