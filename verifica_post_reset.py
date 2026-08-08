"""
verifica_post_reset.py — N47Lab
Monitor della istanza dopo il reset quota (previsto 2026-08-26 ~20:05 UTC).
- Mostra quota, backends, job in coda (QUEUED/RUNNING/DONE/CANCELLED)
- Per i job completati: analizza FFT (subarmonico f=0.5) e MI
- Salva un JSON di sintesi in temp opencode
USO:  python verifica_post_reset.py [--watch-delay 60] [--analyze]
"""
import sys, os, json, time, argparse
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'C:\Users\Utente\Downloads\Esperimento\MatterMemory')
os.chdir(r'C:\Users\Utente\Downloads\Esperimento\MatterMemory')
import pasm_dtc_circuits as P

OUT = r'C:\Users\Utente\AppData\Local\Temp\opencode\report_post_reset.json'

def stampa_quota(S):
    try:
        u = S.usage()
        used = u.get('usage_consumed_seconds', 0)
        lim = u.get('usage_limit_seconds', 0)
        avail = u.get('time_available_at', '?')
        reached = u.get('usage_limit_reached', False)
        print(f"QUOTA: consumati {used}/{lim}s | limit_reached={reached} | disponibile dal: {avail}")
        return u
    except Exception as e:
        print(f"QUOTA: errore {str(e)[:100]}")
        return {}

def estrai_counts(pub):
    """Estrae i conteggi da un pub, gestendo nomi creg diversi ('c', 'sim', ecc.)."""
    if hasattr(pub.data, 'c'):
        return pub.data.c.get_counts()
    for attr in vars(pub.data):
        if attr.startswith('c') or 'meas' in attr:
            obj = getattr(pub.data, attr)
            if hasattr(obj, 'get_counts'):
                return obj.get_counts()
    raise ValueError('nessun creg trovato nel DataBin')

def elenca_job(S, analyze=False):
    jobs = S.jobs(limit=100, descending=True)
    report = []
    for j in jobs:
        st = str(j.status()).upper()
        try:
            bk = j.backend().name
        except Exception:
            bk = '?'
        jid = j.job_id()
        row = {"job_id": jid, "status": st, "backend": bk}
        if st in ("DONE", "COMPLETED", "FINISHED") and analyze:
            try:
                res = j.result()
                n_times = None
                # prova la configurazione nota: usa n da metadata se possibile
                for name, cfg in P.EXPERIMENTS_CONFIG.items():
                    if name.startswith('fft_') and len(res) == cfg.get('n_timesteps', 100):
                        n_times = cfg['n_timesteps']
                if n_times:
                    a = P.analyze_fft_results(res, n_times, 2)
                    row['fft'] = {k: (round(v, 4) if isinstance(v, float) else v)
                                  for k, v in a.items() if k in ('subharmonic_freq', 'subharmonic_peak', 'subharmonic_snr', 'has_subharmonic', 'noise_floor')}
                else:
                    try:
                        mi = P.analyze_mi_results([r for r in res], 2)
                    except Exception:
                        mi = P.analyze_mi_results(res, 2)
                    row['mi'] = {'mi_mean': round(mi['mi_mean'], 5), 'mi_std': round(mi['mi_std'], 5), 'n': len(mi['mi_per_circuit'])}
            except Exception as e:
                row['err_analyze'] = str(e)[:80]
        print(f"  {jid[:18]:<18} | {st:<10} | {bk:<14} |", json.dumps({k: v for k, v in row.items() if k not in ('job_id', 'status', 'backend')})[:120])
        report.append(row)
    return jobs

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--watch', action='store_true', help='attendi fino al termine dei job QUEUED (richiede reset quota)')
    ap.add_argument('--interval', type=int, default=120)
    ap.add_argument('--analyze', action='store_true', help='analizza FFT/MI sui job completati')
    args = ap.parse_args()

    S = P.get_service()
    print("=== N47Lab / post-reset monitor ===")
    u = stampa_quota(S)
    print("\n=== BACKENDS ===")
    for name in ('ibm_kingston', 'ibm_marrakesh', 'ibm_fez'):
        try:
            b = S.backend(name)
            st = b.status()
            print(f"  {name}: coda={st.pending_jobs} operative={st.operational}")
        except Exception as e:
            print(f"  {name}: {str(e)[:60]}")

    while True:
        print("\n=== JOB (ultimi 100) ===")
        report = []
        jobs = elenca_job(S, analyze=args.analyze)
        with open(OUT, 'w') as f:
            json.dump({'usage': u, 'jobs': report}, f, indent=1, default=str)
        print(f"Report salvato: {OUT}")

        if not args.watch:
            break
        queued = [j for j in jobs if 'QUEUED' in str(j.status()).upper()]
        if not queued:
            print("Nessun job in coda: fine monitor.")
            break
        print(f"Ancora {len(queued)} job in coda — nuova verifica tra {args.interval}s...")
        time.sleep(args.interval)

    print("Fatto.")