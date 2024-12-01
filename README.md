# Simulador de Algoritmo de Consenso Raft

## Visão geral

Este projeto implementa uma simulação do algoritmo de consenso distribuído Raft, demonstrando como um sistema distribuído pode manter consistência e tolerância a falhas em vários nós. O algoritmo Raft fornece um mecanismo para eleição de líder, replicação de log e tratamento de falhas de nó em um sistema distribuído.

## O que é o Raft?

Raft é um algoritmo de consenso projetado para ser mais compreensível que os algorítmos da família Paxos, enquanto resolve o mesmo problema fundamental: manter um log consistente em um cluster distribuído de nós. Os princípios-chave do Raft incluem:

1. **Leader Election (Eleição de Líder)**: Os nós elegem um líder para gerenciar a replicação de log
2. **Log Replication (Replicação de Log)**: O líder garante que todos os nós tenham as mesmas entradas de log
3. **Safety (Segurança)**: Garante que todos os nós vejam a mesma progressão da máquina de estado

## Principais Componentes

### Estado dos Nós
Os nós podem estar em um dos três estados:
- **Follower (Seguidor)**: Estado padrão, aguardando instruções do líder
- **Candidate (Candidato)**: Iniciando uma eleição para se tornar líder
- **Leader (Líder)**: Gerenciando o cluster e replicando logs

### Detalhes da Implementação do Algoritmo

#### Leader Election (Eleição do Líder)
1. When a follower doesn't receive heartbeats, it becomes a candidate
2. The candidate increments its term and requests votes from other nodes
3. If a majority of nodes vote in favor, the candidate becomes the leader

#### Fault Tolerance (Tolerância a Falhas)
- Os nós têm tempos limite de eleição aleatórios para evitar votos divididos
- Os líderes enviam heartbeats periódicos para manter a liderança
- Os nós podem se recuperar de falhas e se juntar novamente ao cluster

## Instruções para a Execução

### Executando a simulação

```bash
python app.py
```

### Configurable Parameters

Você pode modificar a simulação ajustando esses parâmetros na seção `__main__`:
- `num_nodes`: Número de nós no cluster (padrão: 5)
- `failure_probability`: Chance de falha do nó (padrão: 0.5)
- `simulation_duration`: Duração da simulação em segundos (padrão: 10)

## Falhas e Respostas Simuladas

A simulação inclui três cenários de falha:

1. **Node Crashes (Falhas de Nó)**: 
   - Um nó pode falhar aleatoriamente durante a simulação
   - Outros nós continuam a funcionar
   - O nó com falha se recupera e se junta novamente ao cluster

2. **Leader Failures (Falhas de Líderes)**:
   - Se o líder falhar, uma nova eleição é acionada
   - Um novo líder é eleito dos nós restantes
   - A consistência do log é mantida

3. **Network Partitions (Partições de Rede)** (Modelo Simplificado):
   - Os nós podem detectar incompatibilidades de termos
   - Os nós ajustam seu estado com base nas mensagens recebidas
   - O sistema converge para um estado consistente

## Logging

A simulação gera logs detalhados:
- Salvo em um arquivo `raft_simulation.log` após a execução
- Inclui timestamps, estados de nós e eventos-chave
- Ajuda a entender o comportamento do cluster

## Limitações

Esta é uma simulação simplificada do Raft que demonstra conceitos básicos. Uma implementação de nível de produção incluiria:
- Replicação de log mais robusta
- Armazenamento persistente
- Cenários de falha de rede mais complexos
- Falta do desenvolvimento de testes para a aplicação
