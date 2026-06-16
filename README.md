# Trabalho Final de Sistemas Operacionais

Simulador de escalonamento de processos usando **Round Robin com Feedback**.

## Grupo

- Aluno 1: FABRÍCIO BECKER
- Aluno 2: GABRIEL ALOÍSIO KETTERMANN
- Aluno 3: JOÃO VITOR KRABBE
- Aluno 4: NÍCOLAS LEANDRO FIUZA CARDOSO

## Linguagem utilizada

Python 3

## Premissas do escalonador

- Quantum: 3 unidades de tempo.
- Número de processos: 5 processos gerados automaticamente.
- Tempos de CPU: sorteados entre 4 e 12 unidades de tempo.
- Dispositivos de I/O: disco, fita magnética, impressora ou nenhum.
- Tempos de I/O:
  - Disco: 4 unidades.
  - Fita magnética: 5 unidades.
  - Impressora: 8 unidades.
- Critério de geração dos processos: os processos são gerados no início da simulação e entram na fila de alta prioridade.
- Semente aleatória: 42, para manter a simulação reprodutível.
- Feedback:
  - Processo que esgota o quantum volta para a fila de baixa prioridade.
  - Processo que retorna do disco volta para a fila de baixa prioridade.
  - Processo que retorna da fita ou impressora volta para a fila de alta prioridade.

## Como executar o projeto

### Execução local

```bash
python src/main.py
```

Caso o comando `python` não esteja disponível, use:

```bash
python3 src/main.py
```

### Bônus Docker

Construir a imagem:

```bash
docker build -t so-escalonador-grupo-2 .
```

Executar o simulador:

```bash
docker run --rm so-escalonador-grupo-2
```

## O que aparece na saída

O simulador imprime a evolução dos processos ao longo do tempo, incluindo:

- criação dos processos;
- entrada na CPU;
- preempção por fim de quantum;
- bloqueio por I/O;
- retorno de I/O para a fila correta;
- finalização dos processos;
- resumo com preempções, eventos de I/O, CPU ociosa, tempo médio de espera e turnaround médio.

## Limitações conhecidas

- Todos os processos são criados no instante inicial da simulação.
- Cada processo realiza no máximo um evento de I/O.
- A fila de I/O é única, mas os tempos de bloqueio são descontados em paralelo.
