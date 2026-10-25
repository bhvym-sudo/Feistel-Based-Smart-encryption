# FeistelGrid Lab

FeistelGrid Lab is a web simulation for the **Lightweight Feistel-Based Smart
Meter Encryption Suite** mini-project. It combines a readable FastAPI backend
with an interactive browser dashboard.

The custom cipher is intentionally limited to an 8-bit block. It is useful for
learning and measurement, but it is not suitable for protecting real billing
data.

## Features

- Realistic, repeatable residential electricity readings
- 8-bit Feistel encryption with 4, 6, or 8 rounds
- Round-by-round key, S-box, permutation, and state trace
- Packet framing with IV, sequence number, and separate HMAC integrity tag
- Plaintext avalanche and key-sensitivity experiments
- Host execution-time benchmark and clearly labelled energy estimate
- Responsive frontend and interactive FastAPI documentation

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:8000`. API documentation is available at
`http://127.0.0.1:8000/docs`.

Run the test suite with:

```bash
pytest -q
```

## Project structure

```text
app/
├── main.py                  API routes and application composition
├── models.py                Request validation
├── core/
│   ├── cipher.py            Feistel algorithm and round trace
│   ├── data_generator.py    Replaceable smart-meter data source
│   └── packet.py            Packet framing, IV and integrity tag
├── services/
│   └── analysis.py          Avalanche, timing and energy experiments
├── templates/index.html     Dashboard structure
└── static/
    ├── styles.css           Responsive visual design
    └── app.js               UI state and API integration
tests/                       Cipher, generator, packet, analysis and API tests
```

## Teammate integration points

### Replace the dummy-data generator

Implement the `ReadingGenerator` protocol from `app/core/data_generator.py`.
The implementation must provide:

```python
def generate(count, interval_minutes, seed, meter_id) -> list[MeterReading]:
    ...
```

Then replace the `reading_generator` object near the top of `app/main.py`. The
`/api/readings` route and frontend do not need to change.

### Adjust the cipher

S-box, bit permutation, key schedule, and round behavior are isolated in
`app/core/cipher.py`. Keep the `encrypt`, `decrypt`, and trace return formats
stable so the API and visualizer continue working.

### Add a hardware benchmark

Keep Python timing separate from MCU results. Add imported Arduino/Wokwi results
as a new service or endpoint and identify voltage, current, clock rate, compiler,
and number of samples in every exported result.

## API summary

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/readings` | Generate smart-meter readings |
| `POST` | `/api/cipher/encrypt` | Encrypt and return a round trace |
| `POST` | `/api/cipher/decrypt` | Recover an 8-bit plaintext |
| `POST` | `/api/packet/simulate` | Build, verify, and decrypt a meter packet |
| `POST` | `/api/analysis/run` | Compare 4-, 6-, and 8-round configurations |
| `POST` | `/api/automation/start` | Start continuous meter collection |
| `POST` | `/api/automation/stop` | Stop the active automation |
| `GET` | `/api/automation/status` | Read automation state and latest result |
| `GET` | `/api/automation/records` | Read persisted automation-only graph data |
| `DELETE` | `/api/automation/records` | Clear stored automation data |

Automation data is stored in `data/automation.db` and survives browser refreshes
and server restarts. One-shot Simulation runs are never inserted into this
database.

## Security scope

The cipher demonstrates Feistel structure and measurable diffusion. Its block
and key spaces are deliberately small. The packet HMAC uses a separate key to
show that confidentiality alone does not provide integrity. A production smart
meter should use a standardized authenticated cipher and a reviewed key-management
scheme.
