"""
PASM + DTC Discrimination Experiments — Qiskit Circuits
Targets: ibm_kingston, ibm_marrakesh (Heron r2, 156q)
Author: N47Lab
"""

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
import numpy as np
from typing import List, Dict, Optional, Any
import json
import os
import pathlib as _pl
from datetime import datetime

# ============================================================
# CONFIGURAZIONE BACKEND E PARAMETRI
# ============================================================

BACKENDS = {
    "kingston": "ibm_kingston",
    "marrakesh": "ibm_marrakesh",
    "fez": "ibm_fez",
}

# ============================================================
# CREDENZIALI — lette da .env, MAI hardcoded
# ============================================================

def _load_env() -> Dict[str, str]:
    env = {}
    p = _pl.Path(_pl.Path(__file__).resolve().parent) / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env

_ENV = _load_env()


def get_service(token_key: str = "IBM_API_TOKEN_2",
                channel: str = "ibm_cloud",
                instance: str = "auto") -> QiskitRuntimeService:
    """Crea QiskitRuntimeService usando il token reale da .env (o variabile d'ambiente).

    Pattern verificato sui 13 esperimenti QPU completati:
    channel='ibm_cloud' + token + instance='auto'.
    """
    token = os.environ.get(token_key) or _ENV.get(token_key, "")
    if not token:
        raise RuntimeError(f"{token_key} non trovato in .env — impossibile autenticarsi")
    return QiskitRuntimeService(channel=channel, token=token, instance=instance)

# ============================================================
# PRE-FLIGHT CHECKS (qiskit-ibm-catalog)
# ============================================================

def check_runtime_capacity(service: QiskitRuntimeService, min_capacity: float = 0.1) -> Dict[str, Any]:
    """
    Controlla capacità runtime rimanente via service.usage() (nessun job, nessun costo).
    Returns: dict con capacity info e boolean 'has_capacity'
    """
    try:
        usage = service.usage()
        remaining = float(usage.get('remainingSeconds', 0) or 0)
        total = float(usage.get('totalSeconds', 0) or 0)
        used = float(usage.get('usedSeconds', 0) or 0)
        has_capacity = remaining >= min_capacity
        return {
            "remaining": remaining,
            "total": total,
            "used": used,
            "has_capacity": has_capacity,
            "message": f"Runtime capacity: {remaining:.1f}/{total:.1f}s rimanenti" if total > 0 else "Usage data unavailable"
        }
    except Exception as e:
        return {
            "remaining": 0,
            "total": 0,
            "used": 0,
            "has_capacity": False,
            "message": f"Errore controllo capacity: {e}"
        }

def check_backend_access(service: QiskitRuntimeService, backend_name: str) -> Dict[str, Any]:
    """
    Verifica accesso a un backend specifico tramite il service autenticato.
    """
    try:
        backend_info = service.backend(backend_name)
        has_access = backend_info is not None
        return {
            "backend": backend_name,
            "has_access": has_access,
            "info": backend_info,
            "message": f"Accesso a {backend_name}: {'OK' if has_access else 'NEGATO'}"
        }
    except Exception as e:
        return {
            "backend": backend_name,
            "has_access": False,
            "info": None,
            "message": f"Errore verifica accesso {backend_name}: {e}"
        }

def check_backends_reachable(service: QiskitRuntimeService) -> Dict[str, Any]:
    """
    Lista tutti i backend raggiungibili dall'istanza (service.backends()).
    """
    try:
        backends_list = [b.name for b in service.backends()]
        return {
            "backends": backends_list,
            "count": len(backends_list),
            "message": f"Backend raggiungibili: {len(backends_list)}"
        }
    except Exception as e:
        return {
            "backends": [],
            "count": 0,
            "message": f"Errore lista backend: {e}"
        }

def find_least_busy_backend(service: QiskitRuntimeService, backend_names: List[str]) -> Dict[str, Any]:
    """
    Trova il backend meno congestionato tra quelli specificati (via status.pending_jobs).
    """
    try:
        best, best_n = None, None
        for name in backend_names:
            b = service.backend(name)
            n = int(b.status().pending_jobs or 0)
            if best_n is None or n < best_n:
                best, best_n = name, n
        return {
            "least_busy": best,
            "message": f"Backend meno congestionato: {best} (coda={best_n})"
        }
    except Exception as e:
        return {
            "least_busy": None,
            "message": f"Errore ricerca least_busy: {e}"
        }

def preflight_check(service: QiskitRuntimeService, 
                    backend_names: List[str], 
                    min_capacity: float = 0.1) -> Dict[str, Any]:
    """
    Controllo pre-flight completo prima di sottomettere job.
    Valida: capacity, accesso backend, almeno 1 backend disponibile.
    Returns: dict con risultati e boolean 'ready_to_submit'
    """
    results = {
        "capacity": check_runtime_capacity(service),
        "backends_reachable": check_backends_reachable(service),
        "backend_access": {},
        "least_busy": None,
        "ready_to_submit": False,
        "errors": []
    }
    
    # Check access per ogni backend richiesto
    for bk in backend_names:
        access = check_backend_access(service, bk)
        results["backend_access"][bk] = access
        if not access["has_access"]:
            results["errors"].append(f"Nessun accesso a {bk}")
    
    # Check capacity
    if not results["capacity"]["has_capacity"]:
        results["errors"].append(f"Capacity insufficiente: {results['capacity']['message']}")
    
    # Check almeno 1 backend disponibile
    if results["backends_reachable"]["count"] == 0:
        results["errors"].append("Nessun backend raggiungibile")
    
    # Trova least_busy tra quelli accessibili
    accessible = [bk for bk, acc in results["backend_access"].items() if acc["has_access"]]
    if accessible:
        lb = find_least_busy_backend(service, accessible)
        results["least_busy"] = lb
    
    # Pronto se nessun errore
    results["ready_to_submit"] = len(results["errors"]) == 0
    
    return results

# Qubit layout (heavy-hex) — triplette adiacenti per M3/3q
QUBIT_TRIPLETS = {
    "kingston": [
        [0, 1, 2],    # tripletta lineare
        [3, 5, 8],    # triangolo heavy-hex
        [12, 13, 14], # altra zona chip
    ],
    "marrakesh": [
        [0, 1, 2],
        [3, 5, 8],
        [12, 13, 14],
    ],
    "fez": [
        [0, 1, 2],
        [3, 5, 8],
        [12, 13, 14],
    ],
}

# Coppie per distance test
DISTANCE_PAIRS = {
    "kingston": [
        [0, 1],   # nearest neighbor
        [0, 3],   # next-nearest
        [0, 12],  # far
    ],
    "marrakesh": [
        [0, 1],
        [0, 3],
        [0, 12],
    ],
    "fez": [
        [0, 1],
        [0, 3],
        [0, 12],
    ],
}

# Parametri sperimentali
EXPERIMENTS_CONFIG = {
    "pasm_base": {
        "backend": ["kingston", "marrakesh"],
        "shots": 8192,
        "qubits": 2,
        "phi_values": [np.pi/2],
        "reps": 1,
    },
    "phi_scan": {
        "backend": ["kingston", "marrakesh"],
        "shots": 8192,
        "qubits": 2,
        "phi_values": np.linspace(0, 2*np.pi, 34).tolist(),
        "reps": 1,
    },
    "echo_hahn": {
        "backend": ["kingston"],
        "shots": 8192,
        "qubits": 2,
        "phi_values": [np.pi/2],
        "reps": 1,
    },
    "delay_sweep": {
        "backend": ["kingston"],
        "shots": 8192,
        "qubits": 2,
        "phi_values": [np.pi/2],
        "delays_ns": np.arange(100, 2100, 100).tolist(),  # 100ns - 2μs
        "reps": 1,
    },
    "frequency_sweep": {
        "backend": ["marrakesh"],
        "shots": 8192,
        "qubits": 2,
        "phi_values": [np.pi/2],
        "freqs_mhz": np.linspace(0.5, 5.0, 16).tolist(),
        "reps": 1,
    },
    "fft_subharmonic_discovery": {
        "backend": ["marrakesh"],
        "shots": 32768,
        "qubits": 2,
        "phi_values": [np.pi/2],
        "freq_mhz": 2.0,
        "n_timesteps": 100,
        "reps": 1,
        "conditional": False,
    },
    "fft_subharmonic_precision": {
        "backend": ["marrakesh"],
        "shots": 65536,
        "qubits": 2,
        "phi_values": [np.pi/2],
        "freq_mhz": 2.0,
        "n_timesteps": 100,
        "reps": 1,
        "conditional": True,  # SOLO se discovery conferma picco
    },
    "m3_3q_readout": {
        "backend": ["kingston"],
        "shots": 8192,
        "qubits": 3,
        "triplets": "all",
        "reps": 1,
    },
    "vz_tomography": {
        "backend": ["kingston"],
        "shots": 8192,
        "qubits": 2,
        "phi_values": [0, np.pi/4, np.pi/2, 3*np.pi/4, np.pi],
        "reps": 1,
    },
}

# ============================================================
# FUNZIONI COSTRUTTRICI CIRCUITI
# ============================================================

def build_pasm_circuit(qubits: List[int], phi: float, n_qubits: int = 2) -> QuantumCircuit:
    """
    PASM base: H^N -> CP(phi) pairwise -> H^N -> measure
    """
    qr = QuantumRegister(max(qubits) + 1, 'q')
    cr = ClassicalRegister(n_qubits, 'c')
    qc = QuantumCircuit(qr, cr)

    # State preparation: |+>^N
    for q in qubits[:n_qubits]:
        qc.h(qr[q])

    # Phase drive: CP(phi) on pairs
    for i in range(n_qubits - 1):
        qc.cp(phi, qr[qubits[i]], qr[qubits[i+1]])

    # Readout basis: X-basis measurement (H before measure)
    for q in qubits[:n_qubits]:
        qc.h(qr[q])

    # Measure
    for i, q in enumerate(qubits[:n_qubits]):
        qc.measure(qr[q], cr[i])

    return qc


def build_pasm_h_circuit(qubits: List[int], phi: float, n_qubits: int = 2) -> QuantumCircuit:
    """
    PASM-H: extra H before CP converts phase to population
    H^N -> CP(phi) -> H^N -> measure (no final H)
    """
    qr = QuantumRegister(max(qubits) + 1, 'q')
    cr = ClassicalRegister(n_qubits, 'c')
    qc = QuantumCircuit(qr, cr)

    for q in qubits[:n_qubits]:
        qc.h(qr[q])

    for i in range(n_qubits - 1):
        qc.cp(phi, qr[qubits[i]], qr[qubits[i+1]])

    for q in qubits[:n_qubits]:
        qc.h(qr[q])

    # NO final H — readout in Z basis
    for i, q in enumerate(qubits[:n_qubits]):
        qc.measure(qr[q], cr[i])

    return qc


def build_echo_hahn_circuit(qubits: List[int], phi: float, n_qubits: int = 2) -> QuantumCircuit:
    """
    Echo/Hahn: H^N -> CP(phi/2) -> X^N -> CP(phi/2) -> H^N -> measure
    Refocusing ZZ/VZ errors
    """
    qr = QuantumRegister(max(qubits) + 1, 'q')
    cr = ClassicalRegister(n_qubits, 'c')
    qc = QuantumCircuit(qr, cr)

    for q in qubits[:n_qubits]:
        qc.h(qr[q])

    # First half CP
    for i in range(n_qubits - 1):
        qc.cp(phi/2, qr[qubits[i]], qr[qubits[i+1]])

    # Pi pulses (echo)
    for q in qubits[:n_qubits]:
        qc.x(qr[q])

    # Second half CP
    for i in range(n_qubits - 1):
        qc.cp(phi/2, qr[qubits[i]], qr[qubits[i+1]])

    for q in qubits[:n_qubits]:
        qc.h(qr[q])

    for i, q in enumerate(qubits[:n_qubits]):
        qc.measure(qr[q], cr[i])

    return qc


def build_delay_sweep_circuit(qubits: List[int], phi: float, delay_ns: int, n_qubits: int = 2) -> QuantumCircuit:
    """
    Delay sweep: H^N -> CP(phi) -> delay -> H^N -> measure
    Tests ZZ residual (MI ∝ sin²(π·ν_ZZ·τ))
    """
    qr = QuantumRegister(max(qubits) + 1, 'q')
    cr = ClassicalRegister(n_qubits, 'c')
    qc = QuantumCircuit(qr, cr)

    for q in qubits[:n_qubits]:
        qc.h(qr[q])

    for i in range(n_qubits - 1):
        qc.cp(phi, qr[qubits[i]], qr[qubits[i+1]])

    # Idle delay (in dt units: 1 dt = 0.222 ns on Heron)
    dt = 0.222e-9
    delay_dt = int(delay_ns * 1e-9 / dt)
    for q in qubits[:n_qubits]:
        qc.delay(delay_dt, qr[q], unit='dt')

    for q in qubits[:n_qubits]:
        qc.h(qr[q])

    for i, q in enumerate(qubits[:n_qubits]):
        qc.measure(qr[q], cr[i])

    return qc


def build_frequency_sweep_circuit(qubits: List[int], phi: float, freq_mhz: float, n_qubits: int = 2) -> QuantumCircuit:
    """
    Frequency sweep: drive at frequency ω during CP
    Implement via Rz(ω·t) during CP or parametric CP
    """
    qr = QuantumRegister(max(qubits) + 1, 'q')
    cr = ClassicalRegister(n_qubits, 'c')
    qc = QuantumCircuit(qr, cr)

    for q in qubits[:n_qubits]:
        qc.h(qr[q])

    # CP with phase evolution at freq_mhz
    # Approximate via Rz rotation during CP
    for i in range(n_qubits - 1):
        qc.cp(phi, qr[qubits[i]], qr[qubits[i+1]])
        # Add virtual Z for frequency drive
        phase = 2 * np.pi * freq_mhz * 1e6 * 500e-9  # 500ns CP gate
        qc.rz(phase, qr[qubits[i]])
        qc.rz(phase, qr[qubits[i+1]])

    for q in qubits[:n_qubits]:
        qc.h(qr[q])

    for i, q in enumerate(qubits[:n_qubits]):
        qc.measure(qr[q], cr[i])

    return qc


def build_fft_circuit(qubits: List[int], phi: float, n_timesteps: int, n_qubits: int = 2) -> List[QuantumCircuit]:
    """
    Subharmonic FFT: stroboscopic measurement at each drive cycle
    Returns list of circuits for each timestep
    """
    circuits = []
    for t_idx in range(n_timesteps):
        qr = QuantumRegister(max(qubits) + 1, 'q')
        cr = ClassicalRegister(n_qubits, 'c')
        qc = QuantumCircuit(qr, cr)

        for q in qubits[:n_qubits]:
            qc.h(qr[q])

        # CP drive at each timestep
        for i in range(n_qubits - 1):
            qc.cp(phi, qr[qubits[i]], qr[qubits[i+1]])

        # Stroboscopic readout at cycle t_idx
        # Add delay for t_idx * T_drive
        dt = 0.222e-9
        T_drive_ns = 500  # CP gate ~500ns
        delay_dt = int(t_idx * T_drive_ns * 1e-9 / dt)
        for q in qubits[:n_qubits]:
            qc.delay(delay_dt, qr[q], unit='dt')

        for q in qubits[:n_qubits]:
            qc.h(qr[q])

        for i, q in enumerate(qubits[:n_qubits]):
            qc.measure(qr[q], cr[i])

        circuits.append(qc)

    return circuits


def build_m3_readout_circuits(triplet: List[int]) -> List[QuantumCircuit]:
    """
    M3 readout characterization: prepare all 8 basis states, measure
    Returns 8 circuits for 3-qubit readout matrix
    """
    circuits = []
    for state_idx in range(8):
        qr = QuantumRegister(max(triplet) + 1, 'q')
        cr = ClassicalRegister(3, 'c')
        qc = QuantumCircuit(qr, cr)

        # Prepare computational basis state |state_idx>
        for i, q in enumerate(triplet):
            if (state_idx >> i) & 1:
                qc.x(qr[q])

        for i, q in enumerate(triplet):
            qc.measure(qr[q], cr[i])

        circuits.append(qc)

    return circuits


def build_vz_tomography_circuits(qubits: List[int], phi: float) -> List[QuantumCircuit]:
    """
    VZ phase tomography: prepare |+>, apply VZ(θ), measure in X/Y/Z
    """
    circuits = []
    bases = ['x', 'y', 'z']
    for basis in bases:
        qr = QuantumRegister(max(qubits) + 1, 'q')
        cr = ClassicalRegister(2, 'c')
        qc = QuantumCircuit(qr, cr)

        for q in qubits:
            qc.h(qr[q])

        # Virtual Z phase (simulatable)
        for q in qubits:
            qc.rz(phi, qr[q])

        # Readout basis
        for q in qubits:
            if basis == 'x':
                qc.h(qr[q])
            elif basis == 'y':
                qc.sdg(qr[q])
                qc.h(qr[q])

        for i, q in enumerate(qubits):
            qc.measure(qr[q], cr[i])

        circuits.append(qc)

    return circuits


# ============================================================
# BUILDER PRINCIPALE PER TUTTI GLI ESPERIMENTI
# ============================================================

def build_all_experiments(config: Dict = EXPERIMENTS_CONFIG) -> Dict[str, List[QuantumCircuit]]:
    """Genera tutti i circuiti per tutti gli esperimenti configurati"""
    all_circuits = {}

    for exp_name, exp_cfg in config.items():
        if exp_cfg.get("conditional", False):
            # Marca come condizionale
            all_circuits[exp_name] = {"circuits": [], "conditional": True, "config": exp_cfg}
            continue

        circuits = []
        backends = exp_cfg["backend"]
        shots = exp_cfg["shots"]
        qubits_list = []

        # Determina qubits da usare
        for bk in backends:
            if exp_cfg.get("triplets") == "all":
                qubits_list.extend(QUBIT_TRIPLETS[bk])
            elif "distance" in exp_name:
                qubits_list.extend(DISTANCE_PAIRS[bk])
            else:
                qubits_list.append(list(range(exp_cfg["qubits"])))

        for qubits in qubits_list:
            if exp_name == "pasm_base":
                for phi in exp_cfg["phi_values"]:
                    circuits.append(build_pasm_circuit(qubits, phi, exp_cfg["qubits"]))

            elif exp_name == "phi_scan":
                for phi in exp_cfg["phi_values"]:
                    circuits.append(build_pasm_circuit(qubits, phi, exp_cfg["qubits"]))

            elif exp_name == "echo_hahn":
                for phi in exp_cfg["phi_values"]:
                    circuits.append(build_echo_hahn_circuit(qubits, phi, exp_cfg["qubits"]))

            elif exp_name == "delay_sweep":
                for delay in exp_cfg["delays_ns"]:
                    for phi in exp_cfg["phi_values"]:
                        circuits.append(build_delay_sweep_circuit(qubits, phi, delay, exp_cfg["qubits"]))

            elif exp_name == "frequency_sweep":
                for freq in exp_cfg["freqs_mhz"]:
                    for phi in exp_cfg["phi_values"]:
                        circuits.append(build_frequency_sweep_circuit(qubits, phi, freq, exp_cfg["qubits"]))

            elif exp_name.startswith("fft_"):
                phi = exp_cfg["phi_values"][0]
                freq = exp_cfg.get("freq_mhz", 2.0)
                n_ts = exp_cfg["n_timesteps"]
                # Build stroboscopic circuits
                fft_circs = build_fft_circuit(qubits, phi, n_ts, exp_cfg["qubits"])
                circuits.extend(fft_circs)

            elif exp_name == "m3_3q_readout":
                triplets = exp_cfg.get("triplets", "all")
                if triplets == "all":
                    for bk in backends:
                        for triplet in QUBIT_TRIPLETS[bk]:
                            circuits.extend(build_m3_readout_circuits(triplet))
                else:
                    for triplet in triplets:
                        circuits.extend(build_m3_readout_circuits(triplet))

            elif exp_name == "vz_tomography":
                for phi in exp_cfg["phi_values"]:
                    circuits.extend(build_vz_tomography_circuits(qubits, phi))

        all_circuits[exp_name] = {"circuits": circuits, "config": exp_cfg}

    return all_circuits


# ============================================================
# TRANSPILAZIONE E SUBMISSION
# ============================================================

def transpile_for_backend(circuits: List[QuantumCircuit], backend_name: str, optimization_level: int = 1) -> List[QuantumCircuit]:
    """Transpila circuiti per backend specifico (optimization_level=1 preserva barrier/delay)"""
    service = get_service()
    backend = service.backend(BACKENDS[backend_name])
    pm = generate_preset_pass_manager(optimization_level=optimization_level, backend=backend)
    return [pm.run(c) for c in circuits]


def auto_select_backend(service: QiskitRuntimeService, preferred: List[str] = None) -> str:
    """
    Seleziona automaticamente il backend migliore (least pending_jobs).
    """
    if preferred is None:
        preferred = ["ibm_kingston", "ibm_marrakesh", "ibm_fez"]

    try:
        lb = find_least_busy_backend(service, preferred)
        if lb["least_busy"]:
            print(f"Auto-selected backend: {lb['least_busy']}")
            return lb["least_busy"]
        raise RuntimeError(lb.get("message", "unknown"))
    except Exception as e:
        print(f"Auto-select failed: {e}, using first preferred: {preferred[0]}")
        return preferred[0]


def submit_jobs_auto(circuits_by_exp: Dict, shots: int, preferred_backends: List[str] = None) -> Dict[str, str]:
    """
    Sottomette job selezionando automaticamente il backend migliore (least_busy)
    con pre-flight checks completi.
    """
    service = get_service()
    
    if preferred_backends is None:
        preferred_backends = ["ibm_kingston", "ibm_marrakesh", "ibm_fez"]
    
    # Auto-select best backend
    backend_name = auto_select_backend(service, preferred_backends)
    print(f"=== AUTO-SELECTED BACKEND: {backend_name} ===")
    
    # PRE-FLIGHT CHECK
    print(f"=== PRE-FLIGHT CHECK per {backend_name} ===")
    preflight = preflight_check(service, [backend_name])
    
    print(f"  Capacity: {preflight['capacity']['message']}")
    print(f"  Backend reachable: {preflight['backends_reachable']['message']}")
    print(f"  Backend access: {preflight['backend_access'][backend_name]['message']}")
    if preflight['least_busy']:
        print(f"  Least busy: {preflight['least_busy']['message']}")
    
    if not preflight['ready_to_submit']:
        print(f"  ❌ PRE-FLIGHT FALLITO: {preflight['errors']}")
        return {exp_name: "PRE-FLIGHT FAILED" for exp_name in circuits_by_exp.keys()}
    
    print(f"  ✅ PRE-FLIGHT OK - Procedo con submission")
    
    backend = service.backend(BACKENDS.get(backend_name, backend_name))
    sampler = SamplerV2(mode=backend)

    job_ids = {}
    for exp_name, exp_data in circuits_by_exp.items():
        if exp_data.get("conditional", False):
            job_ids[exp_name] = "CONDITIONAL - not submitted"
            continue

        circuits = exp_data["circuits"]
        if not circuits:
            continue

        # Transpila
        transpiled = transpile_for_backend(circuits, backend_name)

        # Submit
        job = sampler.run(transpiled, shots=shots)
        job_ids[exp_name] = job.job_id()
        print(f"Submitted {exp_name} on {backend_name}: {job.job_id()} ({len(transpiled)} circuits)")

    return job_ids


def submit_jobs(circuits_by_exp: Dict, backend_name: str, shots: int) -> Dict[str, str]:
    """Sottomette job per esperimento su backend (SamplerV2 mode=backend, NO session) con pre-flight checks"""
    service = get_service()
    
    # PRE-FLIGHT CHECK
    print(f"=== PRE-FLIGHT CHECK per {backend_name} ===")
    preflight = preflight_check(service, [backend_name])
    
    print(f"  Capacity: {preflight['capacity']['message']}")
    print(f"  Backend reachable: {preflight['backends_reachable']['message']}")
    print(f"  Backend access: {preflight['backend_access'][backend_name]['message']}")
    if preflight['least_busy']:
        print(f"  Least busy: {preflight['least_busy']['message']}")
    
    if not preflight['ready_to_submit']:
        print(f"  ❌ PRE-FLIGHT FALLITO: {preflight['errors']}")
        return {exp_name: "PRE-FLIGHT FAILED" for exp_name in circuits_by_exp.keys()}
    
    print(f"  ✅ PRE-FLIGHT OK - Procedo con submission")
    
    backend = service.backend(BACKENDS[backend_name])
    sampler = SamplerV2(mode=backend)

    job_ids = {}
    for exp_name, exp_data in circuits_by_exp.items():
        if exp_data.get("conditional", False):
            job_ids[exp_name] = "CONDITIONAL - not submitted"
            continue

        circuits = exp_data["circuits"]
        if not circuits:
            continue

        # Transpila
        transpiled = transpile_for_backend(circuits, backend_name)

        # Submit
        job = sampler.run(transpiled, shots=shots)
        job_ids[exp_name] = job.job_id()
        print(f"Submitted {exp_name} on {backend_name}: {job.job_id()} ({len(transpiled)} circuits)")

    return job_ids


# ============================================================
# ANALISI AUTOMATICA RISULTATI
# ============================================================

def _estrai_counts(pub_result):
    """Estrae i conteggi da un pub, gestendo nomi creg diversi ('c', 'sim', ecc.)."""
    if hasattr(pub_result.data, 'c'):
        return pub_result.data.c.get_counts()
    for attr in vars(pub_result.data):
        if attr.startswith('c') or 'meas' in attr:
            obj = getattr(pub_result.data, attr)
            if hasattr(obj, 'get_counts'):
                return obj.get_counts()
    raise ValueError('nessun creg trovato nel DataBin')


def analyze_fft_results(job_result, n_timesteps: int, n_qubits: int = 2) -> Dict:
    """Analizza risultati FFT per picco subarmonico a f=0.5 (period doubling, ω/2).

    Con campionamento stroboscopico a 1 campione per ciclo di drive:
    - la fondamentale (1 ciclo/step) appare a f=0.0 (alias DC),
    - la subarmonica a ω/2 (period-doubling) appare a f=0.5 cicli/step
      → indice = argmin(|freqs - 0.5|).
    """
    z_t = []
    for pub_result in job_result:
        counts = _estrai_counts(pub_result)
        total = sum(counts.values())
        p00 = counts.get('00', 0) / total
        p11 = counts.get('11', 0) / total
        p01 = counts.get('01', 0) / total
        p10 = counts.get('10', 0) / total
        z_exp = p00 + p11 - p01 - p10
        z_t.append(z_exp)

    z_t = np.array(z_t, dtype=float)
    fft_vals = np.fft.rfft(z_t)
    freqs = np.fft.rfftfreq(n_timesteps, d=1.0)
    abs_v = np.abs(fft_vals)

    # Peak alle frequenze fisiche rilevanti (robusto al fattore n Timestep)
    sub_idx = int(np.argmin(np.abs(freqs - 0.5)))
    dc_idx = 0
    pk_fd = None
    if len(freqs) > sub_idx + 1:
        band = abs_v.copy()
        band[dc_idx] = 0.0
        band[sub_idx] = 0.0
        if band.max() > 0:
            pk_fd = float(np.abs(fft_vals[int(np.argmax(band))]))

    # Rumore di fondo: escludi DC e finestra attorno alla subarmonica
    mask = np.ones(len(abs_v), dtype=bool)
    mask[dc_idx] = False
    lo = max(0, sub_idx - 1)
    hi = min(len(abs_v), sub_idx + 2)
    mask[lo:hi] = False
    floor = float(np.std(abs_v[mask])) if mask.sum() > 2 else 0.0
    sub_peak = float(abs_v[sub_idx])
    snr = sub_peak / (floor + 1e-12) if abs_v[mask].size > 2 else 0.0

    # Criterio: picco subarmonico rilevato se SNR > 3σ sopra il rumore di fondo
    has_sub = bool(snr > 3.0)

    return {
        "z_t": z_t.tolist(),
        "fft_magnitude": abs_v.tolist(),
        "freqs": freqs.tolist(),
        "subharmonic_freq": float(freqs[sub_idx]),
        "subharmonic_peak": sub_peak,
        "dc_peak": float(abs_v[dc_idx]),
        "dominant_peak": float(pk_fd or 0.0),
        "subharmonic_snr": snr,
        "noise_floor": floor,
        "has_subharmonic": has_sub,
    }


def analyze_mi_results(job_result, n_qubits: int = 2) -> Dict:
    """Calcola MI da conteggi"""
    mi_vals = []
    for pub_result in job_result:
        counts = _estrai_counts(pub_result)
        total = sum(counts.values())
        # Joint probs
        p_xy = {k: v/total for k, v in counts.items()}
        # Marginals
        p_x = {str(i): 0 for i in range(2)}
        p_y = {str(i): 0 for i in range(2)}
        for bitstr, prob in p_xy.items():
            p_x[bitstr[0]] += prob
            p_y[bitstr[1]] += prob

        # MI
        mi = 0
        for (bx, by), p_xy_val in p_xy.items():
            if p_xy_val > 0 and p_x[bx] > 0 and p_y[by] > 0:
                mi += p_xy_val * np.log2(p_xy_val / (p_x[bx] * p_y[by]))
        mi_vals.append(mi)

    return {
        "mi_per_circuit": mi_vals,
        "mi_mean": float(np.mean(mi_vals)),
        "mi_std": float(np.std(mi_vals)),
    }


# ============================================================
# MAIN: GENERA E SALVA CIRCUITI
# ============================================================

if __name__ == "__main__":
    print("=== Building all PASM + DTC discrimination circuits ===")
    all_experiments = build_all_experiments()

    # Summary
    total_circuits = 0
    for exp_name, exp_data in all_experiments.items():
        if exp_data.get("conditional", False):
            print(f"  {exp_name}: CONDITIONAL (skipped)")
            continue
        n = len(exp_data["circuits"])
        total_circuits += n
        print(f"  {exp_name}: {n} circuits")

    print(f"\nTotal circuits: {total_circuits}")

    # Salva metadata per submission
    metadata = {
        "generated": datetime.now().isoformat(),
        "experiments": {k: {"n_circuits": len(v["circuits"]) if not v.get("conditional") else 0,
                            "conditional": v.get("conditional", False),
                            "config": v["config"]} for k, v in all_experiments.items()},
        "backends": BACKENDS,
        "qubit_triplets": QUBIT_TRIPLETS,
        "distance_pairs": DISTANCE_PAIRS,
    }

    with open("pasm_dtc_experiments_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    print("\nMetadata saved to pasm_dtc_experiments_metadata.json")
    print("\nReady for transpilation and submission.")
    print("Usage:")
    print("  from pasm_dtc_circuits import submit_jobs, submit_jobs_auto, transpile_for_backend")
    print("  circuits = build_all_experiments()")
    print("  # Manual submit with pre-flight:")
    print("  job_ids = submit_jobs(circuits, 'kingston', 8192)")
    print("  # Auto-select best backend with pre-flight:")
    print("  job_ids = submit_jobs_auto(circuits, 8192)")

# ============================================================
# AER SIMULATION VALIDATION (pre-QPU)
# ============================================================

def validate_on_aer(circuits_by_exp: Dict, noise_model=None) -> Dict:
    """Valida circuiti su AerSimulator prima di QPU"""
    from qiskit_aer import AerSimulator

    if noise_model:
        backend = AerSimulator.from_backend(noise_model)
    else:
        backend = AerSimulator()

    results = {}
    for exp_name, exp_data in circuits_by_exp.items():
        if exp_data.get("conditional", False):
            continue
        circuits = exp_data["circuits"]
        if not circuits:
            continue

        job = backend.run(circuits, shots=1024)  # Low shots for validation
        result = job.result()
        results[exp_name] = result

    return results