# T-one STT models

The STT service (`ml/stt_tone`) loads T-one models from this directory via `StreamingCTCPipeline.from_local(...)`.

## Setup

1. **Install T-one** (if not already):  
   https://github.com/voicekit-team/T-one

2. **Obtain model files** and place them here so that this directory contains whatever the T-one library expects for `from_local()` (e.g. checkpoint, config, vocabulary). Check the T-one repo for the exact layout and download links (e.g. Hugging Face or release assets).

3. **Or use another path**: set the environment variable when starting the STT service:
   ```bash
   export TONE_MODELS_DIR=/path/to/your/tone_models
   uvicorn ml.stt_tone.app:app --host 0.0.0.0 --port 9001
   ```

Until this directory contains the required model files (or `TONE_MODELS_DIR` points to such a directory), POST `/stt` will return 500.
