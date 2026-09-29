---
title: SIH Urban Flood Depth Inference
emoji: 🌧️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# SIH Urban Flood Depth Inference API

This Docker Space loads the project's existing RandomForest artifact and exposes a small JSON API for the Vercel dashboard. It accepts the selected rainfall inputs and returns per-edge estimates for the bundled Dwarka pilot graph.

The current forest is a surrogate trained on formula-derived/synthetic targets. Its output is not independently validated against measured street-water depths, so deploying the artifact does not make the result an observed or verified flood prediction.

## Configure the Space

1. Create a **private Model repository** and upload the artifact. With the Hugging Face CLI authenticated, from the project root run:

   ```powershell
   hf upload <account>/sih-flood-model models/dwarka_hydraulic_model.pkl dwarka_hydraulic_model.pkl --private
   ```

   The file is about 1.53 GB. Hugging Face's current `hf upload` supports large uploads and can resume them when repeated.
2. Create a **Docker Space** and upload the contents of this directory to the Space repository root. From the project root, the CLI command is:

   ```powershell
   hf upload <account>/sih-flood-inference deploy/hf-inference . --repo-type space
   ```

   Create the Space first and replace `<account>` with your Hugging Face namespace.
3. In the Space settings, add `MODEL_REPO_ID` with the Model repository ID (for example, `your-account/sih-flood-model`). Add `HF_TOKEN` as a Space secret with read access to the private model repository.
4. Optionally add `API_BEARER_TOKEN` as a Space secret. If set, every `/predict` request must include that token.
5. Wait for the Space to build and for the model to download and load. Check `/healthz`; `model_loaded` must be `true` before connecting the dashboard.
6. Set `SIH_RF_INFERENCE_URL` in the Vercel project to `https://<space-subdomain>.hf.space/predict`. If `API_BEARER_TOKEN` is set, also add the same value to Vercel as `SIH_RF_INFERENCE_TOKEN`.
7. Redeploy Vercel. The dashboard API will use HF predictions when configured and healthy; otherwise it keeps its current formula estimate and reports which method produced the result.

The Space downloads the model once into its runtime cache. Space disk is ephemeral by default, so a restart may require another model download. For a private/reliable setup, use an attached Hugging Face model-repository volume or storage bucket when available, or the Hub cache; Google Drive `gdown` is intentionally not used because a large file download can be rate-limited and is less predictable during cold starts.

## Render Web Service alternative

The same FastAPI service can run on Render without creating a Hugging Face Space. The Hugging Face Model repository remains private storage; Render downloads the artifact using a read-only `HF_TOKEN`. The Docker command honours Render's `PORT` variable while keeping port `7860` as the default for a Docker Space.

1. In Render, create a **Web Service** from this Git repository. Set **Root Directory** to `deploy/hf-inference` and use the Docker runtime.
2. Add these environment variables in the Render service settings (keep the token in Render Secrets; never commit it):

   ```text
   MODEL_REPO_ID=harsh070804/sih-2026-model
   MODEL_FILENAME=dwarka_hydraulic_model.pkl
   MODEL_REVISION=main
   HF_TOKEN=<read-token-for-the-private-model-repository>
   API_BEARER_TOKEN=<long-random-secret>
   ```

3. Deploy and open `https://<render-service>.onrender.com/healthz`. Continue only when the response contains `"model_loaded": true` and `"edge_count": 5`.
4. In Vercel, set `SIH_RF_INFERENCE_URL` to `https://<render-service>.onrender.com/predict` and `SIH_RF_INFERENCE_TOKEN` to the same value as Render's `API_BEARER_TOKEN`. Redeploy Vercel. Confirm a dashboard API response reports `depth_model_backend` as `random_forest_huggingface` before describing RandomForest as the active deployed backend.

**Render Free is not suitable for this artifact.** Its web-service plan has 512 MB RAM, while the pickle alone is about 1.53 GB and loading it requires additional memory for Python, NumPy, pandas, and the forest. Free services also sleep after 15 minutes idle and their filesystem is ephemeral; a restart can trigger another large model download. Use a paid plan with at least 4 GB RAM for this uncompressed artifact, or first produce and measure a compact model that fits the selected plan. A successful HF model upload by itself does not provide inference compute.

The `/healthz` request in the setup log used a placeholder URL and returned 404; it does not verify a Render deployment. Replace it with the real service URL after the Web Service is created.

## API

`GET /healthz` returns service/model readiness without exposing credentials.

`POST /predict` body:

```json
{
  "rain_mm": 4.2,
  "rain_3h_accumulated": 7.8,
  "radar_reflectivity_dbz": 23.1,
  "imperviousness_ratio": 0.85
}
```

The dashboard passes forecast-model precipitation, not radar or gauge observations. Keep this Space's bundled graph and feature-range JSON synchronized with `src/dwarka_drainage_graph.json` and `models/training_feature_ranges.json` when those files change.

## Model compatibility and security

The Space pins scikit-learn 1.7.2 (the version installed in the current project environment), but the artifact does not embed reliable training-environment metadata. If the artifact was trained with a different version, confirm that version and update the pin before relying on it; scikit-learn does not guarantee compatibility across arbitrary pickle versions. Only load a pickle from a repository you control: pickle/joblib artifacts can execute code when loaded.
