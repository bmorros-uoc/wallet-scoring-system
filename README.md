# 🚀 Wallet Scoring System

**Diseño e implementación de un sistema explicable de reputación para wallets Web3 basado en datos on-chain.**

Este proyecto constituye un prototipo funcional (MVP) de una herramienta que analiza y calcula la reputación y confiabilidad de una dirección (wallet) de criptomonedas, basándose exclusivamente en su conducta observable dentro de la blockchain de Ethereum (datos on-chain).

El sistema está diseñado para ser **explicable, transparente y reproducible**, utilizando un modelo basado en reglas y ponderaciones fácilmente interpretables. 

---

## ✨ Características Clave e Indicadores

El sistema de puntuación genera un **score global (0-100)** y asigna un perfil cualitativo, basándose en la evaluación de los siguientes indicadores, cada uno con un peso configurable (la suma de pesos es 100%):

* **Longevity Score (Antigüedad):** Mide la edad de la billetera (desde su primera transacción), correlacionando la antigüedad con la estabilidad y continuidad.
* **Activity Score (Actividad):** Evalúa la cantidad y la regularidad de las transacciones, así como el volumen de operaciones, como signo de uso auténtico.
* **Diversity Score (Diversidad):** Cuantifica la variedad de protocolos o tokens con los que ha interactuado la wallet, sugiriendo experiencia y comportamiento exploratorio legítimo.
* **Risk Score (Riesgo General):** Identifica interacciones con contratos que han sido identificados como fraudulentos o direcciones conocidas de scam.
* **Asset Risk Score (Riesgo de Activos):** Evalúa la interacción de la wallet con tokens o activos (ERC-20) marcados como de alto riesgo (ej: *privacy coins* o tokens asociados a *mixers*).

---

## ⚙️ Arquitectura del Sistema

El proyecto sigue una arquitectura modular de ingeniería de datos y desarrollo de software, estructurado en tres fases (ingesta, almacenamiento/procesamiento y scoring).

### Tecnologías

| Componente | Tecnología | Propósito |
| :--- | :--- | :--- |
| **Backend** | Python, FastAPI | Encargado de la lógica de negocio, la recolección de datos y el cálculo del score. |
| **Data Ingestion** | Etherscan API | Fuente principal de datos públicos on-chain (transacciones ETH y tokens ERC-20). |
| **Base de Datos** | DuckDB | Base de datos ligera, sin necesidad de servidor, utilizada para el almacenamiento temporal y la normalización de los datos extraídos. |

### Estructura del Directorio

```bash
wallet-scoring-system/
├── backend/
│   ├── data_ingestion.py       # Ingesta desde API y almacenamiento en DuckDB
│   ├── scoring_model.py        # Lógica del cálculo de indicadores y score final
│   └── main.py                 # Endpoints FastAPI y orquestación general
│
├── data/
│   └── wallet_data.duckdb      # Base de datos local (ignorada por Git)
│
├── .env                        # Variables de entorno (API Key, etc.) (ignorada por Git)
└── requirements.txt            # Dependencias del proyecto
```

## 🛠️ Getting Started (Configuración y Ejecución)

### Prerrequisitos

* Python 3.8+
* Clave API de Etherscan (necesaria para `data_ingestion.py`).

...
