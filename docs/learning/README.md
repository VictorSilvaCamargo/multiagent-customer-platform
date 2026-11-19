# Notas de Aprendizado Técnico

Espaço dedicado para registrar descobertas técnicas relevantes observadas durante o desenvolvimento de cada fase.

## Fase 1 — Dia 1

- **Orçamento real de VRAM vs VRAM nominal:** Uma GPU de 8 GB em uso no Windows (compositor gráfico + IDE) possui tipicamente ~6,3 GB livres para inferência; modelos 4B quantizados em 4-bit mantêm 100% das camadas na GPU com folga para o KV cache.
- **Modo `thinking` no Qwen3.5 e Tool Calling:** Modelos Qwen3.5 possuem raciocínio nativo controlável pelo parâmetro `think` na API do Ollama. Controlar `think=False` em turnos orientados a ferramentas reduz latência e evita raciocínio excessivo antes da emissão de `tool_calls`.
