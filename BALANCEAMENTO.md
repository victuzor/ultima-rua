# Validação local

Execução em 16/09/2026, Python 3.14.6 e pygame-ce 2.5.8, configuração padrão e semente 42.

| Cenário | Estratégia | Sobrevivência | Eliminados | Máximo de áreas | Máximo de NPCs atualizados por passo | Média por passo |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Patrulha / 45 NPCs | Parado | 6,3 s | 0 | 1 | 5 | 0,008 ms |
| Patrulha / 45 NPCs | Rota + itens | **75 s / vitória** | 25 | 4 | 20 | 0,017 ms |
| Cerco / 450 NPCs | Parado | 4,2 s | 0 | 1 | 50 | 0,043 ms |
| Cerco / 450 NPCs | Rota + itens | 51,0 s | 53 | 4 | 186 | 0,092 ms |
| Enxame / 3000 NPCs | Parado | 3,3 s | 0 | 1 | 333 | 0,351 ms |
| Enxame / 3000 NPCs | Rota + itens | 11,9 s | 92 | 4 | 1286 | 0,522 ms |

As médias incluem a estratégia automática e a troca de áreas em disco, mas excluem renderização. Variam conforme o computador e não equivalem ao FPS do jogo.

A rota segue quatro pontos fixos, usa cura com saúde até 60 e dispara quando há hostis a menos de 65 unidades. Ela não procura itens deliberadamente nem tenta otimizar a sobrevivência. Patrulha serve como introdução; Cerco exige maior cuidado com recursos; Enxame é um cenário de dificuldade e carga elevadas.

Foram aprovados 16 testes automatizados das regras e o teste de inicialização/renderização em modo sem janela. O arquivo `previa-zumbis.png` mostra a interface atual renderizada.

Para reproduzir, execute `benchmark.py` e os comandos de validação do README. Para comparar ajustes, altere `activation_distance` (sempre menor que metade da área), `pulse_radius` (no máximo a distância de ativação), `enemy_damage_per_second` e `survival_seconds` no `config.json`, e execute o benchmark novamente.
