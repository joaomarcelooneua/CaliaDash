# Calia Y2 · Inventário Inteligente

Dashboard em Streamlit que traduz o diagnóstico da AP2 (Programação Estruturada) em uma experiência visual coerente com a identidade Calia. O app usa os dados de `data/valores.xlsx` para evidenciar:

- **Concentração do orçamento** em Macs (R$ 2.145/ano) e licenças premium (R$ 1.200/ano), reforçando a necessidade de padronização por função.
- **Falta de rastreabilidade**: itens sem responsável ou sem número de inventário, justificando a implantação de um inventário vivo com QR Code e centro de custo.
- **Impacto discreto dos itens de baixo custo** (mouses, teclados, adaptadores e fontes) que, em volume, corroem o orçamento.

## Pré-requisitos

- Python 3.10+
- Dependências listadas em `requirements.txt`

## Como executar

```bash
python -m venv .venv
.venv\\Scripts\\activate      # Windows PowerShell
pip install -r requirements.txt
streamlit run app.py
```

O Streamlit abrirá automaticamente em `http://localhost:8501`.

## Estrutura

- `app.py`: aplicação Streamlit com tema customizado inspirado na identidade Calia.
- `data/valores.xlsx`: planilha original usada no diagnóstico.
- `requirements.txt`: dependências mínimas para leitura do Excel, análise e visualização.

## Sobre os indicadores

Para manter coerência total com o diagnóstico fornecido, a depreciação anual de Macs e licenças é calculada usando os valores de referência (R$ 2.145 e R$ 1.200). Os demais itens seguem os números da planilha. Essa abordagem permite que métricas, textos e gráficos reforcem exatamente as conclusões apresentadas no relatório.
