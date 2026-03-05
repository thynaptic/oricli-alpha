# Technology Stack: Mavaia Core

## Language & Runtime
- **Python (3.11+)**: The primary programming language, leveraging modern features and type hinting.

## Machine Learning & Reasoning
- **PyTorch**: The foundational framework for transformer model training and execution.
- **JAX & Flax**: Used for optimized numerical computing and specific reasoning architectures.
- **Transformers (Hugging Face)**: Core library for working with state-of-the-art LLM architectures and tokenizers.
- **PEFT (Hugging Face)**: Utilized for Parameter-Efficient Fine-Tuning (LoRA) of specialized elective adapters.
- **TensorFlow**: Supported for specific module implementations and legacy compatibility.

## API & Backend
- **FastAPI**: Used to provide a high-performance, asynchronous, OpenAI-compatible HTTP API.
- **Uvicorn**: Asynchronous server gateway interface (ASGI) for running the FastAPI application.

## User Interface
- **Flask**: Used for the lightweight, interactive testing UI.
- **Vanilla CSS & JS**: Primary technologies for UI components to ensure flexibility and low overhead.

## Data & Integration
- **Hugging Face Datasets**: Used for loading and processing curriculum training data.
- **Wikipedia API**: Integrated for external knowledge retrieval.
- **Internet Archive API**: Integrated for discovering and retrieving public domain texts.
- **HTTPX & Requests**: Used for robust synchronous and asynchronous network communication.

## Infrastructure & DevOps
- **Docker**: Used for containerization and consistent execution environments.
- **RunPod**: The primary platform for GPU-accelerated remote training, with custom dynamic matching for hardware efficiency.
- **AWS S3 / RunPod S3**: Used for persistent storage of models, checkpoints, and code archives.

## Development Tools
- **Black**: Enforced for consistent code formatting.
- **Ruff**: Used for high-speed linting and code quality checks.
- **MyPy**: Utilized for static type checking to ensure code robustness.
