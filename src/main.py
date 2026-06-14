# ==========================================
# CONFIGURAÇÕES GERAIS DO SISTEMA
# ==========================================
ESTADOS = ["NOVO", "PRONTO", "EXECUTANDO", "BLOQUEADO", "FINALIZADO"]
PRIORIDADES = ["ALTA", "BAIXA"]
QUANTUM = 3

# Tempos fixos de bloqueio por dispositivo
DISPOSITIVOS_IO = {
    "DISCO": 3,
    "FITA": 5,
    "IMPRESSORA": 8,
    "NENHUM": 0
}

global_pid = 1 # Usado para gerar PIDs automaticamente no fork

# ==========================================
# ESTRUTURA DO PCB (Process Control Block)
# ==========================================
def criar_processo(ppid, prioridade, tempo_restante, io_momento, prox_io, fork_momento=-1):
    global global_pid
    p = {
        "pid": global_pid,
        "ppid": ppid,
        "status": ESTADOS[0],             # Inicia como NOVO
        "prioridade": prioridade,         # ALTA ou BAIXA
        "tempo_restante": tempo_restante, # Quanto tempo de CPU precisa
        "io_momento": io_momento,         # Gatilho: quando tempo_restante chegar aqui, faz I/O
        "prox_io": prox_io,               # DISCO, FITA, IMPRESSORA ou NENHUM
        "tempo_io": 0,                    # Cronômetro do bloqueio (preenchido na hora do I/O)
        "fork_momento": fork_momento      # Gatilho para criar processo filho
    }
    global_pid += 1
    return p

# Criando nossa lista inicial de processos com características diferentes
p1 = criar_processo(0, "ALTA", tempo_restante=8, io_momento=5, prox_io="DISCO", fork_momento=6)
p2 = criar_processo(0, "ALTA", tempo_restante=4, io_momento=-1, prox_io="NENHUM")
p3 = criar_processo(0, "BAIXA", tempo_restante=6, io_momento=4, prox_io="IMPRESSORA")
p4 = criar_processo(0, "ALTA", tempo_restante=5, io_momento=3, prox_io="FITA")

processos = [p1, p2, p3, p4]

# ==========================================
# INICIALIZAÇÃO DAS FILAS
# ==========================================
fila_alta = []
fila_baixa = []
fila_io = [] # Fila única para I/O, mas os tempos descontam em paralelo
finalizados = []

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

print("--- INICIANDO SIMULAÇÃO ROUND ROBIN COM FEEDBACK ---\n")

while True:
    # Condição de Parada: Nenhuma fila tem processos e a CPU está vazia
    if not fila_alta and not fila_baixa and not fila_io and cpu_p is None:
        break

    # 1. ESCALONADOR: Puxa o próximo processo se a CPU estiver livre
    if cpu_p is None:
        if fila_alta:
            cpu_p = fila_alta.pop(0)
            cpu_p["status"] = ESTADOS[2] # EXECUTANDO
            qa = QUANTUM
            print(f"[{clock:02d}u] [ESCALONADOR] Processo {cpu_p['pid']} (ALTA) entrou na CPU.")
        elif fila_baixa:
            cpu_p = fila_baixa.pop(0)
            cpu_p["status"] = ESTADOS[2] # EXECUTANDO
            qa = QUANTUM
            print(f"[{clock:02d}u] [ESCALONADOR] Processo {cpu_p['pid']} (BAIXA) entrou na CPU.")

    # 2. PROCESSAMENTO DE I/O (Ocorre em paralelo com a CPU)
    # Iteramos sobre uma cópia da fila [:] para poder remover itens com segurança
    for p_io in fila_io[:]:
        p_io["tempo_io"] -= 1
        
        if p_io["tempo_io"] <= 0:
            print(f"[{clock + 1:02d}u] [I/O] Processo {p_io['pid']} terminou uso de {p_io['prox_io']}. [FEEDBACK: ALTA Prio]")
            p_io["status"] = ESTADOS[1] # PRONTO
            p_io["prioridade"] = "ALTA" # Regra do Feedback: Volta de I/O promovido
            p_io["io_momento"] = -1     # Reseta gatilho de I/O para não repetir infinitamente
            
            fila_alta.append(p_io)
            fila_io.remove(p_io)

    # 3. PROCESSAMENTO DA CPU
    if cpu_p is not None:
        cpu_p["tempo_restante"] -= 1
        qa -= 1
        
        # A. Checa criação de Processo Filho (PPID)
        if cpu_p["tempo_restante"] == cpu_p["fork_momento"]:
            filho = criar_processo(ppid=cpu_p["pid"], prioridade=cpu_p["prioridade"], tempo_restante=3, io_momento=-1, prox_io="NENHUM")
            filho["status"] = ESTADOS[1]
            print(f"[{clock + 1:02d}u] [FORK] Processo {cpu_p['pid']} criou filho PID {filho['pid']} (PPID {filho['ppid']}).")
            if filho["prioridade"] == "ALTA":
                fila_alta.append(filho)
            else:
                fila_baixa.append(filho)
            cpu_p["fork_momento"] = -1 # Reseta para não criar vários filhos

        # B. Checa Finalização do Processo
        if cpu_p["tempo_restante"] == 0:
            print(f"[{clock + 1:02d}u] [CPU] Processo {cpu_p['pid']} FINALIZADO.")
            cpu_p["status"] = ESTADOS[4]
            finalizados.append(cpu_p)
            cpu_p = None

        # C. Checa Requisição de I/O
        elif cpu_p["tempo_restante"] == cpu_p["io_momento"]:
            disp = cpu_p["prox_io"]
            tempo_bloqueio = DISPOSITIVOS_IO[disp]
            cpu_p["tempo_io"] = tempo_bloqueio
            cpu_p["status"] = ESTADOS[3] # BLOQUEADO
            
            print(f"[{clock + 1:02d}u] [CPU] Processo {cpu_p['pid']} pediu I/O ({disp} - {tempo_bloqueio}u). Foi para BLOQUEADO.")
            fila_io.append(cpu_p)
            cpu_p = None

        # D. Checa Fim de Quantum (Round Robin Feedback)
        elif qa == 0:
            print(f"[{clock + 1:02d}u] [CPU] Processo {cpu_p['pid']} esgotou Quantum. [FEEDBACK: BAIXA Prio]")
            cpu_p["status"] = ESTADOS[1] # PRONTO
            cpu_p["prioridade"] = "BAIXA" # Regra do Feedback: Usou todo tempo, é rebaixado
            
            fila_baixa.append(cpu_p)
            cpu_p = None

    # Avança o relógio do sistema
    clock += 1

# ==========================================
# RESUMO FINAL
# ==========================================
print("\n--- SIMULAÇÃO CONCLUÍDA EM", clock, "UNIDADES DE TEMPO ---")
print(f"{'PID':<5} | {'PPID':<5} | {'PRIORIDADE FINAL':<20} | {'STATUS'}")
print("-" * 55)
for p in sorted(finalizados, key=lambda x: x["pid"]):
    print(f"{p['pid']:<5} | {p['ppid']:<5} | {p['prioridade']:<20} | {p['status']}")