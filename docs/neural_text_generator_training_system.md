# Neural Text Generator Training System: A Multi-Source, Profile-Based Training Framework for Local RNN/LSTM Models

**Technical Report TR-2025-01**

**Date:** 2025-01-13

**Version:** v1.0.0

**Authors:** Mavaia Core Engineering Team

---

## Abstract

We describe a comprehensive training framework for neural text generation models that enables local-first, privacy-preserving text generation using RNN/LSTM architectures. This system integrates six heterogeneous data sources—Project Gutenberg, Wikipedia, LibriVox, OpenLibrary, Internet Archive, and HuggingFace—through a unified data abstraction layer. The framework introduces a profile-based configuration system that allows researchers to encode training strategies as reusable YAML configurations, supporting both character-level and word-level generation models. We present the architecture, data integration patterns, training protocols, and evaluation capabilities of this system, which operates entirely within a local cognitive layer without external API dependencies.

---

## Introduction

Local-first text generation remains a critical requirement for cognitive systems that prioritize privacy, autonomy, and deterministic inference pathways. Unlike cloud-based language models that rely on remote APIs, local models provide complete control over the inference process, enable offline operation, and eliminate data transmission risks. However, training effective local models requires sophisticated data management, flexible training configurations, and robust preprocessing pipelines.

This document describes the Neural Text Generator Training System, a framework that addresses these requirements through a modular architecture combining multi-source data integration, profile-based training configuration, and dual-model support (character and word-level RNN/LSTM models). The system is designed to operate within Mavaia's cognitive layer architecture, enabling seamless integration with the broader brain module ecosystem.

We developed this system to support research into adaptive sampling strategies and local-first inference pathways. The framework allows researchers to rapidly experiment with different data sources, training profiles, and model configurations while maintaining consistency across training runs through standardized configuration files.

---

## Architecture Summary

The training system is organized into three primary components: a data abstraction layer, a training orchestration module, and a configuration management system. This separation enables independent evolution of data source implementations while maintaining a consistent interface for training operations.

### Data Abstraction Layer

The system uses a registry-based pattern for data source integration. Each data source implements a common interface that exposes methods for category-based filtering, item ID selection, and raw text extraction. The `NeuralTextGeneratorData` class acts as a facade that routes requests to appropriate source implementations based on runtime configuration.

Data sources are discovered dynamically, allowing new sources to be added without modifying core training logic. The abstraction layer handles differences in data formats, access patterns, and authentication requirements, presenting a uniform interface to the training pipeline.

### Training Orchestration Module

The `NeuralTextGeneratorModule` provides the core training and generation capabilities. It supports two model types: character-level RNNs that operate on individual characters, and word-level models that use word tokenization. Both model types use LSTM architectures implemented via TensorFlow/Keras, enabling GPU acceleration when available.

The module implements operations for model training, text generation, model persistence, and configuration management. Training can proceed for a fixed number of epochs or for a specified duration, allowing researchers to balance training time against model quality.

### Configuration Management System

Training profiles are stored as YAML files in a dedicated profiles directory. Each profile specifies data sources, training parameters, model types, and optional constraints (such as maximum text size or data percentage). The script discovers profiles automatically, allowing researchers to share configurations through version control.

Command-line arguments can override profile settings, providing flexibility for exploratory experiments while preserving standardized configurations for reproducible research. This dual-level configuration approach balances consistency with experimental flexibility.

---

## Capabilities Overview

### Multi-Source Data Integration

The system integrates six data sources, each optimized for different use cases:

- **Project Gutenberg**: Classic literature and public domain texts, organized by category (fiction, technical, philosophy, etc.)

- **Wikipedia**: Contemporary articles across diverse topics, suitable for general-purpose language modeling

- **LibriVox**: Audiobook transcripts, providing conversational and narrative text patterns

- **OpenLibrary**: Bibliographic metadata and full-text access to books, supporting category-based discovery

- **Internet Archive**: Diverse historical and contemporary texts, accessible via the Internet Archive API

- **HuggingFace**: Datasets from the HuggingFace Hub, supporting both public datasets and authenticated private datasets

The data layer supports multi-source training, allowing researchers to combine texts from multiple sources in a single training run. This capability enables domain-specific adaptation while maintaining general language modeling properties.

### Profile-Based Training Configuration

Training profiles encode complete training strategies as YAML configurations. A profile specifies:

- Data sources and selection criteria (categories, item IDs, search terms)
- Training parameters (epochs, duration limits, data percentage)
- Model configuration (character vs. word-level, or both)
- Resource constraints (maximum text size, maximum items per source)

The system includes 30+ pre-configured profiles covering various scenarios: fast training for experimentation, comprehensive training for production models, source-specific profiles (e.g., HuggingFace-only), and domain-specific profiles (e.g., technical texts, literature). Researchers can create custom profiles by adding YAML files to the profiles directory.

### Dual-Model Architecture

The system trains two complementary model types:

- **Character-level models**: Operate on individual characters, enabling fine-grained control over text structure and supporting any character set. These models are memory-efficient and suitable for constrained environments.

- **Word-level models**: Use word tokenization, capturing semantic relationships more effectively but requiring larger vocabularies and more memory. These models typically generate more coherent text at the sentence level.

Both model types can be trained simultaneously, allowing researchers to compare generation quality and choose the appropriate model for specific use cases. The training script can generate samples from both models for side-by-side evaluation.

### Adaptive Sampling and Generation

Text generation supports configurable sampling parameters:

- **Temperature**: Controls randomness in generation (lower values produce more deterministic output)

- **Maximum length**: Limits generation length for computational efficiency

- **Prompt-based generation**: Supports both continuation and prompt-based generation modes

The system provides comprehensive sample generation capabilities, including sentence-level samples, paragraph generation, and multi-prompt evaluation with different temperature settings.

### Evaluation Metrics (Recommended Gates)

For a run to be considered healthy and reproducible, capture at least:

- **final_loss** / **final_val_loss** from Keras training
- **perplexity** (approx.): `exp(final_loss)` (use as a trend metric)
- **epochs_completed** and **training_time_seconds**
- Sample generations at fixed prompts/temperatures (qualitative regression)

The training script writes `run_config.json`, `data_request.json`, and `training_result.json` into a per-run output directory so you can compare runs reliably. You can control the output location via `--run-dir` or use the built-in `scripts/training_profiles/smoke.yaml` profile for quick validation.

For multi-GPU transformer training, you can use the lightweight launcher:

```bash
./.venv/bin/python scripts/launch_distributed_train.py --nproc-per-node 2 -- --profile transformer_gpt2 --model-type transformer
```


### Training Flexibility

Training can proceed via multiple modes:

- **Epoch-based**: Train for a fixed number of epochs
- **Time-based**: Train for a specified duration (minutes or hours), useful for resource-limited environments
- **Data-percentage**: Use a subset of available data for faster experimentation
- **Continue training**: Resume training from existing models, enabling iterative refinement

These options support both rapid experimentation and long-running production training jobs.

---

## Safety & Reliability Summary

The system prioritizes local-first execution, ensuring that all training and inference operations occur within the local environment. No training data or generated text is transmitted to external services, maintaining privacy and data sovereignty.

### Data Handling

The system processes data in memory, with optional disk caching for large datasets. Raw data is not persisted beyond the training session unless explicitly configured. All data sources respect their respective licenses and usage terms, with authentication handled through environment variables or configuration files.

### Model Persistence

Trained models are saved to a configurable model directory, with separate storage for character-level and word-level models. Model persistence includes vocabulary mappings, ensuring that models can be loaded independently of training sessions. The system validates model integrity on load, providing clear error messages if model files are corrupted or incompatible.

### Error Handling

The training script implements comprehensive error handling for missing dependencies, invalid configurations, and data access failures. When optional dependencies (e.g., TensorFlow, PyYAML) are unavailable, the script provides clear guidance on installation requirements. Data source failures are logged but do not terminate training if multiple sources are specified.

### Reproducibility

Training profiles enable reproducible research by encoding complete training configurations. The system logs configuration parameters at training start, allowing researchers to verify that training runs match intended configurations. Model checkpoints include configuration metadata, enabling post-hoc analysis of training conditions.

---

## Limitations

The system has several known limitations that researchers should consider:

**Model Architecture**: The system uses standard RNN/LSTM architectures. These models are less capable than transformer-based language models in terms of long-range dependencies and context handling. Researchers requiring state-of-the-art generation quality may need to consider transformer architectures.

**Data Preprocessing**: Text preprocessing is basic, focusing on whitespace normalization and optional lowercasing. More sophisticated preprocessing (e.g., sentence segmentation, specialized tokenization) is not currently supported.

**Resource Requirements**: Training large models or processing extensive datasets requires significant computational resources. The system does not implement distributed training, limiting scalability for very large datasets.

**Evaluation Metrics**: The system provides qualitative evaluation through sample generation but does not include automated metrics (e.g., perplexity, BLEU scores). Researchers must implement custom evaluation pipelines for quantitative assessment.

**Data Source Availability**: Some data sources require external dependencies (e.g., Internet Archive API, HuggingFace Hub). Availability depends on external service status and network connectivity.

**Vocabulary Management**: Word-level models use simple word-based tokenization. Out-of-vocabulary handling is limited, and vocabulary size management (e.g., frequency-based filtering) is not configurable.

---

## Future Directions

We identify several directions for extending the system's capabilities:

**Architecture Improvements**: Integration of transformer-based architectures (e.g., GPT-style models) would improve generation quality. This would require significant modifications to the training pipeline but could leverage existing data integration and profile management infrastructure.

**Advanced Preprocessing**: Implementation of sophisticated text preprocessing pipelines, including sentence segmentation, part-of-speech tagging, and domain-specific normalization, would improve model training on diverse text sources.

**Evaluation Framework**: Development of automated evaluation metrics and benchmarking capabilities would enable quantitative assessment of model quality across different training configurations.

**Distributed Training**: Support for multi-GPU and distributed training would enable training on larger datasets and more complex models while reducing training time.

**Model Compression**: Integration of model compression techniques (e.g., quantization, pruning) would reduce model size and enable deployment in resource-constrained environments.

**Incremental Learning**: Support for incremental learning on new data without full retraining would enable continuous model improvement as new data becomes available.

**Domain Adaptation**: Enhanced support for fine-tuning pre-trained models on domain-specific data would improve generation quality for specialized use cases.

---

## Conclusion

We have presented a comprehensive training framework for local neural text generation that integrates multiple data sources, supports flexible training configurations through profiles, and enables dual-model architectures. The system prioritizes local-first execution, privacy preservation, and research reproducibility while maintaining flexibility for exploratory research.

The profile-based configuration system allows researchers to encode training strategies as reusable configurations, promoting consistency across experiments while preserving flexibility for parameter exploration. Multi-source data integration enables training on diverse text corpora, supporting both general-purpose and domain-specific models.

While the system has limitations in model architecture and evaluation capabilities, it provides a solid foundation for research into local-first text generation within cognitive systems. Future work will focus on architecture improvements, evaluation frameworks, and scalability enhancements to support more sophisticated generation models.

---

## References

- Mavaia Core Architecture Documentation
- TensorFlow/Keras Documentation: https://www.tensorflow.org/
- Project Gutenberg: https://www.gutenberg.org/
- HuggingFace Datasets: https://huggingface.co/datasets
- Internet Archive API: https://archive.org/developers/

---

*This document follows Thynaptic Publication Style Framework v2.0 (Soft Academic mode)*

