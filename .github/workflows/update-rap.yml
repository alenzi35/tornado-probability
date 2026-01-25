name: Update RAP Tornado Data

on:
  schedule:
    - cron: '15 * * * *'   # runs at :15 past every hour
  workflow_dispatch:        # allows manual run

jobs:
  update:
    runs-on: ubuntu-latest

    steps:
      # 1️⃣ Checkout your repository
      - name: Checkout repo
        uses: actions/checkout@v4

      # 2️⃣ Set up Python
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      # 3️⃣ Install dependencies
      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y libeccodes0 libeccodes-dev
          pip install boto3 xarray numpy cfgrib

      # 4️⃣ Run RAP processing script
      - name: Run RAP processing
        run: python scripts/process_rap.py

      # 5️⃣ Commit updated data
      - name: Commit updated data
        run: |
          git config user.name "github-actions"
          git config user.email "github-actions@github.com"
          git add data/
          git commit -m "Update RAP tornado data" || echo "No changes"
          git push
