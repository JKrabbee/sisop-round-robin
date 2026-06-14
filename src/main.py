import random

# ==========================================
# CONFIGURAÇÕES GERAIS DO SISTEMA
# ==========================================
ESTADOS = ["NOVO", "PRONTO", "EXECUTANDO", "BLOQUEADO", "FINALIZADO"]
PRIORIDADES = ["ALTA", "BAIXA"]
QUANTUM = 3
SEED = 42
TOTAL_PROCESSOS = 5
TEMPO_CPU_MIN = 4
TEMPO_CPU_MAX = 12

# Tempos fixos de bloqueio por dispositivo
DISPOSITIVOS_IO = {
    "DISCO": 4,
    "FITA": 5,
    "IMPRESSORA": 8,
    "NENHUM": 0
}

RETORNO_IO = {
    "DISCO": "BAIXA",
    "FITA": "ALTA",
    "IMPRESSORA": "ALTA",
    "NENHUM": "ALTA"
}

global_pid = 1 # Usado para gerar PIDs automaticamente

# ==========================================
# ESTRUTURA DO PCB (Process Control Block)
# ==========================================
def criar_processo(ppid, prioridade, tempo_restante, io_momento, prox_io):
    global global_pid
    p = {
        "pid": global_pid,
        "ppid": ppid,
        "status": ESTADOS[0],             # Inicia como NOVO
        "prioridade": prioridade,         # ALTA ou BAIXA
        "tempo_total_cpu": tempo_restante, # Tempo original de CPU
        "tempo_restante": tempo_restante, # Quanto tempo de CPU precisa
        "tempo_chegada": 0,               # Instante em que entrou no sistema
        "tempo_inicio": None,             # Primeiro instante em que entrou na CPU
        "tempo_finalizacao": None,        # Instante em que finalizou
        "tempo_total_bloqueado": 0,       # Tempo acumulado em I/O
        "io_momento": io_momento,         # Gatilho: quando tempo_restante chegar aqui, faz I/O
        "prox_io": prox_io,               # DISCO, FITA, IMPRESSORA ou NENHUM
        "tempo_io": 0,                    # Cronômetro do bloqueio (preenchido na hora do I/O)
        "ja_fez_io": False,               # Evita repetir I/O indefinidamente
        "preempcoes": 0                   # Quantas vezes sofreu preempção
    }
    global_pid += 1
    return p

def gerar_processos(qtd_processos):
    processos_gerados = []
    tipos_io = ["DISCO", "FITA", "IMPRESSORA", "NENHUM"]
    ios_sorteados = tipos_io[:]

    while len(ios_sorteados) < qtd_processos:
        ios_sorteados.append(random.choice(tipos_io))

    random.shuffle(ios_sorteados)

    for prox_io in ios_sorteados[:qtd_processos]:
        tempo_cpu = random.randint(TEMPO_CPU_MIN, TEMPO_CPU_MAX)
        io_momento = -1

        if prox_io != "NENHUM":
            io_momento = random.randint(1, tempo_cpu - 1)

        processos_gerados.append(
            criar_processo(
                ppid=0,
                prioridade="ALTA",
                tempo_restante=tempo_cpu,
                io_momento=io_momento,
                prox_io=prox_io
            )
        )

    return processos_gerados

random.seed(SEED)
processos = gerar_processos(TOTAL_PROCESSOS)

# ==========================================
# INICIALIZAÇÃO DAS FILAS
# ==========================================
fila_alta = []
fila_baixa = []
fila_io = [] # Fila única para I/O, mas os tempos descontam em paralelo
finalizados = []
preempcoes_total = 0
cpu_ociosa = 0
eventos_io = {
    "DISCO": 0,
    "FITA": 0,
    "IMPRESSORA": 0
}

for p in processos:
    p["status"] = ESTADOS[1] # Passam de NOVO para PRONTO
    if p["prioridade"] == "ALTA":
        fila_alta.append(p)
    else:
        fila_baixa.append(p)

# ==========================================
# LOOP PRINCIPAL DO SIMULADOR (Clock-based)
# ==========================================
clock = 0
cpu_p = None # Ponteiro para o processo que está na CPU
qa = 0       # Quantum atual

print(f"[config] quantum={QUANTUM} | processos={len(processos)} | seed={SEED}")
print("--- INICIANDO SIMULAÇÃO ROUND ROBIN COM FEEDBACK ---\n")

for p in processos:
    print(f"[t=000] [CRIACAO] Processo {p['pid']} criado -> fila ALTA | cpu={p['tempo_total_cpu']} | io={p['prox_io']}@{p['io_momento']}")

print()

while True:
    # Condição de Parada: Nenhuma fila tem processos e a CPU está vazia
    if not fila_alta and not fila_baixa and not fila_io and cpu_p is None:
        break

    # 1. ESCALONADOR: Puxa o próximo processo se a CPU estiver livre
    if cpu_p is None:
        if fila_alta:
            cpu_p = fila_alta.pop(0)
            cpu_p["status"] = ESTADOS[2] # EXECUTANDO
            if cpu_p["tempo_inicio"] is None:
                cpu_p["tempo_inicio"] = clock
            qa = QUANTUM
            print(f"[t={clock:03d}] [ESCALONADOR] Processo {cpu_p['pid']} (ALTA) entrou na CPU.")
        elif fila_baixa:
            cpu_p = fila_baixa.pop(0)
            cpu_p["status"] = ESTADOS[2] # EXECUTANDO
            if cpu_p["tempo_inicio"] is None:
                cpu_p["tempo_inicio"] = clock
            qa = QUANTUM
            print(f"[t={clock:03d}] [ESCALONADOR] Processo {cpu_p['pid']} (BAIXA) entrou na CPU.")

    if cpu_p is None and not fila_alta and not fila_baixa and fila_io:
        cpu_ociosa += 1
        print(f"[t={clock:03d}] [CPU] Ociosa aguardando I/O.")

    # 2. PROCESSAMENTO DE I/O (Ocorre em paralelo com a CPU)
    # Iteramos sobre uma cópia da fila [:] para poder remover itens com segurança
    for p_io in fila_io[:]:
        p_io["tempo_io"] -= 1
        
        if p_io["tempo_io"] <= 0:
            prioridade_retorno = RETORNO_IO[p_io["prox_io"]]
            print(f"[t={clock + 1:03d}] [I/O] Processo {p_io['pid']} terminou uso de {p_io['prox_io']}. [FEEDBACK: {prioridade_retorno} Prio]")
            p_io["status"] = ESTADOS[1] # PRONTO
            p_io["prioridade"] = prioridade_retorno
            
            if prioridade_retorno == "ALTA":
                fila_alta.append(p_io)
            else:
                fila_baixa.append(p_io)
            fila_io.remove(p_io)

    # 3. PROCESSAMENTO DA CPU
    if cpu_p is not None:
        cpu_p["tempo_restante"] -= 1
        qa -= 1
        
        # A. Checa Finalização do Processo
        if cpu_p["tempo_restante"] == 0:
            print(f"[t={clock + 1:03d}] [CPU] Processo {cpu_p['pid']} FINALIZADO.")
            cpu_p["status"] = ESTADOS[4]
            cpu_p["tempo_finalizacao"] = clock + 1
            finalizados.append(cpu_p)
            cpu_p = None

        # B. Checa Requisição de I/O
        elif cpu_p["tempo_restante"] == cpu_p["io_momento"] and not cpu_p["ja_fez_io"]:
            disp = cpu_p["prox_io"]
            tempo_bloqueio = DISPOSITIVOS_IO[disp]
            cpu_p["tempo_io"] = tempo_bloqueio
            cpu_p["tempo_total_bloqueado"] += tempo_bloqueio
            cpu_p["ja_fez_io"] = True
            cpu_p["status"] = ESTADOS[3] # BLOQUEADO
            if disp in eventos_io:
                eventos_io[disp] += 1
            
            print(f"[t={clock + 1:03d}] [CPU] Processo {cpu_p['pid']} pediu I/O ({disp} - {tempo_bloqueio}u). Foi para BLOQUEADO.")
            fila_io.append(cpu_p)
            cpu_p = None

        # C. Checa Fim de Quantum (Round Robin Feedback)
        elif qa == 0:
            print(f"[t={clock + 1:03d}] [CPU] Processo {cpu_p['pid']} esgotou Quantum. [FEEDBACK: BAIXA Prio]")
            cpu_p["status"] = ESTADOS[1] # PRONTO
            cpu_p["prioridade"] = "BAIXA" # Regra do Feedback: Usou todo tempo, é rebaixado
            cpu_p["preempcoes"] += 1
            preempcoes_total += 1
            
            fila_baixa.append(cpu_p)
            cpu_p = None

    # Avança o relógio do sistema
    clock += 1

# ==========================================
# RESUMO FINAL
# ==========================================
for p in finalizados:
    p["turnaround"] = p["tempo_finalizacao"] - p["tempo_chegada"]
    p["tempo_espera"] = p["turnaround"] - p["tempo_total_cpu"] - p["tempo_total_bloqueado"]

total_finalizados = len(finalizados)
tempo_medio_espera = 0
tempo_medio_turnaround = 0
percentual_cpu_ociosa = 0

if total_finalizados > 0:
    tempo_medio_espera = sum(p["tempo_espera"] for p in finalizados) / total_finalizados
    tempo_medio_turnaround = sum(p["turnaround"] for p in finalizados) / total_finalizados

if clock > 0:
    percentual_cpu_ociosa = (cpu_ociosa / clock) * 100

print("\n--- SIMULAÇÃO CONCLUÍDA EM", clock, "UNIDADES DE TEMPO ---")
print(f"Processos finalizados: {total_finalizados}/{len(processos)}")
print(f"Preempções: {preempcoes_total}")
print(f"Eventos de I/O: DISCO={eventos_io['DISCO']} | FITA={eventos_io['FITA']} | IMPRESSORA={eventos_io['IMPRESSORA']}")
print(f"CPU ociosa: {cpu_ociosa}u ({percentual_cpu_ociosa:.2f}%)")
print(f"Tempo médio de espera: {tempo_medio_espera:.2f}u")
print(f"Turnaround médio: {tempo_medio_turnaround:.2f}u")
print(f"{'PID':<5} | {'PPID':<5} | {'PRIO FINAL':<10} | {'STATUS':<10} | {'ESPERA':<8} | {'TURNAROUND'}")
print("-" * 78)
for p in sorted(finalizados, key=lambda x: x["pid"]):
    print(f"{p['pid']:<5} | {p['ppid']:<5} | {p['prioridade']:<10} | {p['status']:<10} | {p['tempo_espera']:<8} | {p['turnaround']}")
