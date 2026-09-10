# Quickstart Guide

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run data pipeline:
   ```bash
   python src/data_pipeline.py
   ```
3. Generate drainage graph:
   ```bash
   python src/drainage_graph_model.py
   ```
4. Train model:
   ```bash
   python src/model_train.py
   ```
5. Start backend server:
   ```bash
   python src/main.py
   ```
6. Open `http://localhost:8081/` in a browser.

## Usage
- Use the map to view real‑time flood depth.
- Click **Safe Route Finder** to get flood‑safe navigation.
- Switch between Live and Demo modes via the mode selector.

## Notes
- Ensure the `hello.gif` asset is present in the `assets` folder.
- The system requires internet access for radar and weather APIs.
