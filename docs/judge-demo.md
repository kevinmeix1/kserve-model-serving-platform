# Judge Demo

## Start the live system

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e '.[serving,test,demo]'
make demo
make api-run PYTHON=.venv/bin/python
```

Open `http://127.0.0.1:8080/dashboard`.

The dashboard includes a **Judge Demo Theater** panel that turns the committed
video into a live review path: serving contract, inference lab, rollout gates,
and LLM/KServe platform depth.

## Five-minute story

1. Establish the champion, challenger, traffic split, canary gate, and current p95 latency.
2. In the Live Inference Lab, increase debt ratio and delinquencies, then run a real V2 inference.
3. Point to route, model revision, score, latency, snapshot generation, and ledger count.
4. Explain why a passing gate recommends an action but does not bypass controlled promotion.
5. Connect the local SQLite WAL proof to a shared transactional ledger in a multi-pod deployment.
6. Finish with rollback, Kueue capacity, Airflow asset state, and OpenTelemetry evidence.

## Generate narration and video

```bash
make demo-voice PYTHON=.venv/bin/python
make demo-video
```

The neural voice is generated with `edge-tts`, which provides natural Microsoft
neural voices without adding heavy model weights to the repository. Local
offline options such as Piper or Kokoro can replace this step if cloud-free
media generation is required. The resulting video is
`docs/demo/kserve-judge-demo.mp4`.
