# Threshold: Policy Engine

**Threshold: Policy Engine** is a high-performance, multi-layered AI governance and security service. Operating as a critical sub-module within the broader **MODELISE** deployment platform, Threshold acts as the definitive security gateway for enterprise machine learning models. It provides real-time prompt evaluation, rigorous policy enforcement, and runtime operational oversight to ensure all AI interactions remain secure, compliant, and cost-effective.

## System Architecture & Execution Flow

Threshold implements a sequential, defense-in-depth architecture designed to intercept, analyze, and authorize AI payloads before they reach the execution environment. The engine is divided into three distinct execution layers.

### 1. Presentation Layer

This is the primary ingress point for all system interactions and API requests.

* **Function:** Handles request normalization, payload extraction, and synchronous API communication.
* **Technical Flow:** Receives raw prompts via REST endpoints, standardizes the input schema, and passes the sanitized data to the evaluation pipeline.

### 2. Primary Evaluation Layer



The first line of defense focusing on rapid, heuristic-based security checks.

* **Function:** Executes low-latency filtering designed to catch immediate violations such as explicit prompt injection attempts, malformed payloads, or hardcoded blocklist triggers.
* **Technical Flow:** If a prompt fails at this layer, the request is immediately terminated, minimizing compute overhead. Approved payloads are seamlessly routed to the next tier.

### 3. Secondary Security Layer



The deep-inspection tier responsible for semantic evaluation and context-aware governance.

* **Function:** Analyzes the nuanced intent of the prompt and the generated model response against complex corporate guidelines.
* **Technical Flow:** This layer interfaces directly with the core policy databases to enforce semantic boundaries, ensuring no sensitive data leakage or behavioral drift occurs during runtime.

## 🛡️ Core Governance Modules

The engine relies on highly configurable, database-backed modules to dictate runtime behavior, mapped out structurally via a comprehensive system ER Diagram.

* **Organizational Policy Engine Rules:** The central nervous system of the module. Administrators can define customized, granular operational rules that dictate exactly what the AI can and cannot generate.


* **Country Pack Integration:** A specialized compliance module designed to handle geographic and regional legal frameworks. It dynamically adjusts data handling and policy enforcement based on localized jurisdiction rules.


* **Spends And Limits:** A critical resource allocation tracker. This module actively monitors API token consumption, compute utilization, and request volume to enforce strict operational budgets and prevent cost overruns.



## 🔌 Local Inference & Model Integration

Threshold is engineered for flexible deployment, including secure environments that require fully isolated, localized inference without external API dependencies.

* **LM Studio Integration:** The engine natively supports local model execution. Administrators can host state-of-the-art open-weight models directly on local hardware on port `1234` using LM Studio.


* **Connection Management:** Features a dedicated Connections module to configure, verify, and maintain stable websockets and HTTP sessions with the local inference server.


* **Test Prompts Pipeline:** Includes a built-in diagnostic suite to execute Test Prompts, allowing developers to safely validate system responses and verify that Organizational Policy Engine Rules are being correctly applied to the local model's output.



## 💻 Technology Stack

* **Core Language:** Python


* **API Routing:** FastAPI / Uvicorn (Seamlessly processing Presentation Layer traffic)
* **Local Inference:** LM Studio (Configured for internal REST API server on Port 1234)


* **Data Layer:** Relational data schemas modeling the internal ER Diagram specifications



## ⚙️ Installation & Deployment

1. **Environment Initialization:**
Clone the repository and isolate the dependencies using a standard Python virtual environment.


```bash
git clone https://github.com/atul-codes/MODELISE.git
cd MODELISE
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

```


2. **Inference Server Configuration:**
* Launch **LM Studio** on your host machine.


* Load the desired GGUF/safetensors model into memory.
* Start the Local Server specifically bound to port `1234`.




3. **Engine Initialization:**
Start the backend FastAPI server to initialize the Presentation Layer.


```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

```


4. **Policy Verification:**
Utilize the engine's built-in Test Prompts interface to run baseline inputs through the Primary Evaluation Layer and Secondary Security Layer, verifying that the output adheres strictly to the loaded Organizational Policy Engine Rules.
