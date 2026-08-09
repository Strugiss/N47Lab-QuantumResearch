# AGENTS.md — MatterMemory (N47Lab)

## Cos'è
Progetto di ricerca su imprint di fase sub-Planckiano come candidato materia oscura, verificato tramite PASM (Phase-Anchored State Multiplexing) su IBM Quantum.

## Architecture
- `mattermemorys.html` — report interattivo principale (v2.7, apri via localhost:8000)
- `n47lab_paper.tex` — paper LaTeX per arXiv
- `Immagini/` — 47 figure PNG/SVG
- Script `.py` in `C:\Users\Utente\AppData\Local\Temp\opencode\` (non nel workspace)
- `backup_v*.html` — backup del report HTML

## Comandi essenziali
| Azione | Comando (da MattterMemory/) |
|--------|-----------------------------|
| HTML preview | `http://localhost:8000/mattermemorys.html` |
| Esegui script | `python <script>.py` nel temp opencode |
| Submit QPU | `SamplerV2(mode=backend)` — **NO** Session/Batch su open plan |
| Export .env | API1=IBM_CRN, API2=IBM_OPEN |

## Backends IBM disponibili (API2, open plan)
- `ibm_kingston` — ~15 job coda (preferito)
- `ibm_marrakesh` — ~500 job
- `ibm_fez` — ~2000 job (congestionato)

## Template submit QPU
```python
S = QiskitRuntimeService(channel='ibm_cloud', token=API2)
backend = S.backend('ibm_kingston')
pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
qc_t = pm.run(qc)
sampler = SamplerV2(mode=backend)
job = sampler.run(qc_t, shots=8192)
```

## Risultati chiave (verificati)
- 14 esperimenti QPU completati (tabella esplicita in n47lab_paper.tex), Z combinato > 50σ
- PASM: MI condivisa 0.063 ± 0.005 (marrakesh) / 0.047 ± 0.004 (kingston)
- Replica 10×: Z = 39.6σ
- φ-scan: MI modulata da φ, picco a π
- PASM Distanza: Z = 34σ, MI indipendente da distanza
- WITNESS controllo: MI = 0.00013 (zero)
- QST/DISCORD: MI=0.728, classico (<0.01)
- Scaling: MI picco a 3q = 0.159

## Credenziali
- `.env` in **DUE posizioni** — IMPORTANTE: i contenuti possono DIVERGERE:
  - `C:\Users\Utente\AppData\Local\Temp\opencode\.env` (per script temp)
  - `C:\Users\Utente\Downloads\Esperimento\MatterMemory\.env` (per workspace — **QUI c'è il token VALIDO**)
- **Token valido IBM_API_TOKEN_2 (prefisso `lWg-…`) SOLO nel .env del workspace** — i token in temp/.env e quelli hardcoded sono morti (revocati/disabled). Verifica validità: `https://iam.cloud.ibm.com/identity/token` con apikey → 200 = OK
- Se i due .env divergono: sincronizza con `_sync_env.py` in temp opencode (copia WS → temp, senza stampare valori)
- API1: IBM Cloud (con CRN), API2: IBM Open (no CRN)
- `config.py`: `load_dotenv()` + variabili d'ambiente
- Account salvato Qiskit: `API2` (channel `ibm_cloud`, istanza open-instance CRN) — NON cancellarlo (Nemotron l'aveva rimosso)
- MAI stampare token in chat; MAI hardcodare token negli script (35 token già ripuliti in 06/2026)

## Vincoli tecnici (non cambiare)
- `optimization_level=1` sempre (preserva barriere/delay)
- **Niente** Session/Batch — solo `SamplerV2(mode=backend)` diretto
- AerSimulator GPU **non disponibile** su Windows (solo CPU 24 thread)
- **Tutto l'output visibile in italiano** (compresi thinking/ragionamenti trascritti in chat)

## File di configurazione opencode
- `.opencode/REGOLE.md` + `REGOLE_VINCOLANTI.md` + `PERSONALITA.md`
- `opencode.json` → `"instructions": [".opencode/REGOLE.md"]`

## Bug legacy noti (non fixare senza richiesta)
1. `chsh_bell_memory.py`: `channel='ibm_quantum'` → deve essere `ibm_cloud`
2. `entanglement_witness_pasm.py`: autenticazione usa channel sbagliato
3. `watch_pasm.py`: errore di indentazione
4. `n47lab_subplanckian_theory.py`: codice sperimentale (bug in fase di sviluppo)

## Workflow tipico
1. Leggi stato file su disco (non fidarti della memoria)
2. Verifica PHP server su localhost:8000 (non avviare senza chiedere)
3. Controlla backends disponibili e code (`verifica_post_reset.py` in workspace)
4. Sviluppa script in temp opencode
5. Per modifiche a `mattermemorys.html`: segui REGOLA 5 (AMBIENTE CHIUSO)
6. Dopo modifica incisiva: link ispezione → attesa approvazione → backup

## Stato istanza QPU (aggiornato 08/08/2026)
- Connessione ripristinata (token valido WS `.env` → `get_service()` in pasm_dtc_circuits.py, channel `ibm_cloud` + instance auto)
- Quota: consumati 798s / limite 600s → **esaurita**, reset atteso **26/08/2026 20:05 UTC** (`time_available_at`)
- **10 job QUEUED** (7 del batch 06/08: 6 kingston + 1 marrakesh; 3 precedenti marrakesh/kingston), 0 job di Nemotron creati il 07-08/08
- Backends: `ibm_kingston` (coda ~1-2), `ibm_marrakesh` (0), `ibm_fez` (0) — tutti operative
- **FIX IMPORTANTE in `analyze_fft_results`**: subarmonica a f=0.5 (indice `n/2`, non `n/4`), SNR robusto senza bias, web mediante `_estrai_counts`
- `verifica_post_reset.py` (nel workspace): monitor quota+job+analisi FFT/MI; uso: `python verifica_post_reset.py --watch --analyze` dopo il reset

## Stato depositi e pubblicazioni (aggiornato 08/08/2026)
- GitHub: 4 repo pubblici (MIT): `N47Lab`, `N47Lab-QuantumResearch`, `pasm-experiments`, `research-timeline` — `desktop-tutorial` ELIMINATO 08/08 (scope `delete_repo` autorizzato). `research-timeline`: **v0.2.0 (09/08/2026)** — restaurata la versione ORIGINALE dello strumento (source: `C:\Users\Utente\Downloads\Esperimento\N47Lab_research_timeline\`): CLI Typer+pydantic+rich, eventi tipizzati (`T0`–`Tn`, `pivot`, `control`, `submission`, `publication`, `milestone`), metriche+evidence (git commit, QPU job IDs, data/code links), `ai_role` disclosure, export LaTeX/Markdown/HTML/JSON-LD, schema JSON draft-07 — sostituisce la versione semplificata YAML/click v0.1 (la cui creazione ha contribuito al rifiuto JOSS #11102: "non research software"). Fix applicati al legacy: validazione ID (regex whitelist), `ai_role` onorato in init, `data_links`/`code_links` in evidence, split virgole. 14 test pytest green; `example/timeline.json` = timeline PASM reale (T0 06/06 → submission 07/08, Z>50σ, MI, job IDs). CI pytest 3.9–3.12 verde (ultimo run 31281095127). Release GitHub v0.2.0+2 commit badge. JOSS rejection #11102: risottomissione possibile da ~08/02/2027 (6 mesi storia pubblica)
- Software Heritage salvataggi OK (via API `GET/POST /api/1/origin/save/?visit_type=git&origin_url=...`; pagina web bloccata da Anubis):
  - `research-timeline` → `swh:1:snp:62a2f748e52113016cf291c4b8c944e86c6848bf` (aggiornato 08/08, id request 2413535; snapshot precedenti `dd1f61f...`, `d60633d...`)
  - `N47Lab` → `swh:1:snp:be5e00f94178b5ed47c797d5d89488710266fc66`
  - `pasm-experiments` → `swh:1:snp:d15ca220b94c566865e5a29eff0bd3208081ba5e`
  - `N47Lab-QuantumResearch` → `swh:1:snp:92f8e6892594857b377ae885532c4e6cfda19b9` (salvato 08/08, id request 2413450)
- JOSS (research-timeline, soggetto: scientific computing): sottomesso 07/08/2026, **RIGETTATO** 08/08 — issue `openjournals/joss-reviews#11102` chiusa (labels pre-review/rejected; motivo principale: repo con <6 mesi sviluppo pubblico + paper.md v0.1 insufficiente + versione semplificata "non research software" → ora risolta con v0.2.0 restaurata). Risottomissione possibile da ~08/02/2027; alternative fino ad allora: pyOpenSci (consigliato), JORS (APC £471), SoftwareX (APC $1560, waiver). Badge stato: `https://joss.theoj.org/papers/fe70f58f29d6cec1531968fd56a6895/status.svg` (text "JOSS JOSS Rejected Rejected")
- APS/PRL (n47lab_paper.tex): nessuna fee obbligatoria (APC ~$2700 solo OA, page charge 830$ opzionale); sottomissione web diretta e rPorta virtuale; affiliazione = dove condotta la ricerca
