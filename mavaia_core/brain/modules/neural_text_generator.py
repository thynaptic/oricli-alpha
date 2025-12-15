"""
Neural Text Generator Module
Local RNN/LSTM text generation with character-level and word-level models
Trained on Project Gutenberg books for natural language generation
"""

from typing import Any, Dict, List, Optional, Tuple
import sys
import json
import random
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata

# Try to import TensorFlow/Keras
TENSORFLOW_AVAILABLE = False
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
    TENSORFLOW_AVAILABLE = True
except ImportError:
    pass

# Try to import numpy
NUMPY_AVAILABLE = False
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    pass

# Import data pipeline
try:
    from neural_text_generator_data import NeuralTextGeneratorData
except ImportError:
    NeuralTextGeneratorData = None


class NeuralTextGeneratorModule(BaseBrainModule):
    """
    Neural text generation using RNN/LSTM models
    Supports both character-level and word-level generation
    """

    def __init__(self):
        self.char_model = None
        self.word_model = None
        self.char_vocab = None
        self.char_vocab_reverse = None
        self.word_vocab = None
        self.word_vocab_reverse = None
        self.config = None
        self.model_dir = None
        self._models_loaded = False
        self._config_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="neural_text_generator",
            version="1.0.0",
            description="Local RNN/LSTM text generation with character-level and word-level models",
            operations=[
                "train_model",
                "generate_text",
                "generate_continuation",
                "load_model",
                "save_model",
                "get_model_info",
            ],
            dependencies=["tensorflow", "numpy"] if TENSORFLOW_AVAILABLE else [],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        self._load_config()
        self._setup_model_directory()
        return True

    def _load_config(self):
        """Load configuration from JSON file"""
        if self._config_loaded:
            return

        config_path = Path(__file__).parent / "neural_text_generator_config.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            else:
                # Use defaults
                self.config = {
                    "model_type": "both",
                    "character_model": {
                        "hidden_size": 256,
                        "num_layers": 2,
                        "embedding_size": 128,
                        "dropout": 0.2,
                    },
                    "word_model": {
                        "hidden_size": 512,
                        "num_layers": 2,
                        "embedding_size": 256,
                        "dropout": 0.2,
                    },
                    "training": {
                        "batch_size": 64,
                        "sequence_length": 100,
                        "learning_rate": 0.001,
                        "epochs": 10,
                        "validation_split": 0.2,
                    },
                    "generation": {
                        "temperature": 0.7,
                        "max_length": 500,
                        "top_k": 50,
                        "top_p": 0.9,
                        "default_model": "character",
                    },
                }
            self._config_loaded = True
        except Exception as e:
            print(
                f"[NeuralTextGenerator] Failed to load config: {e}",
                file=sys.stderr,
            )
            self.config = {}

    def _setup_model_directory(self):
        """Setup model storage directory"""
        if self.model_dir is None:
            self.model_dir = (
                Path(__file__).parent.parent.parent / "models" / "neural_text_generator"
            )
            self.model_dir.mkdir(parents=True, exist_ok=True)
            (self.model_dir / "checkpoints").mkdir(exist_ok=True)

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        if not TENSORFLOW_AVAILABLE:
            return {
                "success": False,
                "error": "TensorFlow/Keras not available. Install with: pip install tensorflow",
            }

        if not NUMPY_AVAILABLE:
            return {
                "success": False,
                "error": "NumPy not available. Install with: pip install numpy",
            }

        if operation == "train_model":
            return self._train_model(params)
        elif operation == "generate_text":
            return self._generate_text(params)
        elif operation == "generate_continuation":
            return self._generate_continuation(params)
        elif operation == "load_model":
            return self._load_model(params)
        elif operation == "save_model":
            return self._save_model(params)
        elif operation == "get_model_info":
            return self._get_model_info()
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _train_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Train character-level and/or word-level models
        
        Args:
            params:
                - model_type: "character", "word", or "both" (default: "both")
                - book_ids: List of Gutenberg book IDs (optional)
                - categories: List of categories to load (e.g., ["fiction", "technical"])
                - epochs: Number of training epochs (optional, overridden by time limits)
                - continue_training: Whether to continue from existing model (optional)
                - train_for_minutes: Maximum training time in minutes (optional)
                - train_for_hours: Maximum training time in hours (optional)
                - max_text_size: Maximum text size in characters (optional)
                - max_books: Maximum number of books to load (optional)
                - data_percentage: Percentage of data to use (0.0-1.0, optional)
        
        Returns:
            Training result dictionary
        """
        if NeuralTextGeneratorData is None:
            return {
                "success": False,
                "error": "Data pipeline not available",
            }

        model_type = params.get("model_type", self.config.get("model_type", "both"))
        book_ids = params.get("book_ids")
        categories = params.get("categories")
        epochs = params.get("epochs", self.config.get("training", {}).get("epochs", 10))
        continue_training = params.get("continue_training", False)
        train_for_minutes = params.get("train_for_minutes")
        train_for_hours = params.get("train_for_hours")
        max_text_size = params.get("max_text_size")
        max_books = params.get("max_books", self.config.get("data", {}).get("max_books", 3))
        data_percentage = params.get("data_percentage", 1.0)

        # Calculate time limit in seconds
        time_limit_seconds = None
        if train_for_hours:
            time_limit_seconds = train_for_hours * 3600
        elif train_for_minutes:
            time_limit_seconds = train_for_minutes * 60

        try:
            # Load and preprocess data
            print("[NeuralTextGenerator] Loading training data...", file=sys.stderr)
            raw_text = NeuralTextGeneratorData.load_gutenberg_data(
                book_ids=book_ids,
                max_books=max_books,
                categories=categories,
                max_text_size=max_text_size,
            )
            
            # Apply data percentage if specified
            if data_percentage < 1.0:
                text_length = int(len(raw_text) * data_percentage)
                raw_text = raw_text[:text_length]
                print(
                    f"[NeuralTextGenerator] Using {data_percentage*100:.1f}% of data ({text_length:,} characters)",
                    file=sys.stderr,
                )
            
            preprocess_config = self.config.get("data", {}).get("preprocessing", {})
            text = NeuralTextGeneratorData.preprocess_text(
                raw_text,
                lowercase=preprocess_config.get("lowercase", True),
                remove_special=preprocess_config.get("remove_special", True),
            )

            results = {}

            # Train character model
            if model_type in ["character", "both"]:
                print("[NeuralTextGenerator] Training character-level model...", file=sys.stderr)
                char_result = self._train_character_model(
                    text, epochs, continue_training, time_limit_seconds
                )
                results["character"] = char_result

            # Train word model
            if model_type in ["word", "both"]:
                print("[NeuralTextGenerator] Training word-level model...", file=sys.stderr)
                word_result = self._train_word_model(
                    text, epochs, continue_training, time_limit_seconds
                )
                results["word"] = word_result

            return {
                "success": True,
                "results": results,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Training failed: {str(e)}",
            }

    def _train_character_model(
        self, text: str, epochs: int, continue_training: bool, time_limit_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Train character-level model
        
        Args:
            text: Training text
            epochs: Number of epochs (may be limited by time)
            continue_training: Whether to continue from existing model
            time_limit_seconds: Maximum training time in seconds (None = no limit)
        """
        sequence_length = self.config.get("training", {}).get("sequence_length", 100)
        start_time = time.time()
        
        # Create sequences
        sequences, targets = NeuralTextGeneratorData.create_character_sequences(
            text, sequence_length=sequence_length
        )

        if not sequences:
            return {"success": False, "error": "No sequences created"}

        # Build vocabulary
        self.char_vocab = NeuralTextGeneratorData.build_character_vocabulary(text)
        self.char_vocab_reverse = {idx: char for char, idx in self.char_vocab.items()}
        vocab_size = len(self.char_vocab)
        
        # Save vocabulary immediately so it's available even if training is interrupted
        try:
            char_meta_path = self.model_dir / "char_model.json"
            metadata = {
                "vocab": self.char_vocab,
                "config": self.config.get("character_model", {}),
            }
            with open(char_meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            print(
                f"[NeuralTextGenerator] Warning: Could not save vocabulary: {e}",
                file=sys.stderr,
            )

        # Convert to arrays
        X, y = NeuralTextGeneratorData.sequences_to_arrays_char(
            sequences, targets, self.char_vocab
        )

        # Split into train/validation
        val_split = self.config.get("training", {}).get("validation_split", 0.2)
        split_idx = int(len(X) * (1 - val_split))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        # Build or load model
        if continue_training and self.char_model is None:
            self._load_model({"model_type": "character"})

        if self.char_model is None:
            char_config = self.config.get("character_model", {})
            self.char_model = self._build_character_model(
                vocab_size=vocab_size,
                embedding_dim=char_config.get("embedding_size", 128),
                hidden_size=char_config.get("hidden_size", 256),
                num_layers=char_config.get("num_layers", 2),
                dropout=char_config.get("dropout", 0.2),
            )

        # Compile model
        learning_rate = self.config.get("training", {}).get("learning_rate", 0.001)
        self.char_model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
            loss="categorical_crossentropy",
            metrics=["accuracy"],
        )

        # Train with time limit support
        batch_size = self.config.get("training", {}).get("batch_size", 64)
        
        # Custom callback for time-based training and checkpoint saving
        class TrainingCallback(keras.callbacks.Callback):
            def __init__(self, time_limit: Optional[float], start_time: float, model_dir: Path, model_type: str):
                self.time_limit = time_limit
                self.start_time = start_time
                self.should_stop = False
                self.model_dir = model_dir
                self.model_type = model_type

            def on_epoch_end(self, epoch, logs=None):
                # Check time limit
                if self.time_limit:
                    elapsed = time.time() - self.start_time
                    if elapsed >= self.time_limit:
                        print(
                            f"\n[NeuralTextGenerator] Time limit reached ({elapsed:.1f}s), stopping training",
                            file=sys.stderr,
                        )
                        self.model.stop_training = True
                        self.should_stop = True
                
                # Save checkpoint after each epoch
                try:
                    checkpoint_path = self.model_dir / "checkpoints" / f"{self.model_type}_model_epoch_{epoch+1}.h5"
                    self.model.save(checkpoint_path)
                    
                    # Also save as latest model (for easy loading after interruption)
                    latest_path = self.model_dir / f"{self.model_type}_model_latest.h5"
                    self.model.save(latest_path)
                    
                    print(
                        f"[NeuralTextGenerator] Checkpoint saved: epoch {epoch+1}",
                        file=sys.stderr,
                    )
                except Exception as e:
                    print(
                        f"[NeuralTextGenerator] Warning: Could not save checkpoint: {e}",
                        file=sys.stderr,
                    )

        callbacks = []
        callbacks.append(TrainingCallback(time_limit_seconds, start_time, self.model_dir, "character"))
        
        # Adjust epochs if time limit is very short
        effective_epochs = epochs
        if time_limit_seconds:
            # Estimate time per epoch (rough estimate: 1 epoch per 30 seconds for small models)
            estimated_epoch_time = 30.0
            max_epochs_by_time = int(time_limit_seconds / estimated_epoch_time) + 1
            effective_epochs = min(epochs, max_epochs_by_time)
            print(
                f"[NeuralTextGenerator] Time limit: {time_limit_seconds:.1f}s, "
                f"adjusting to {effective_epochs} epochs max",
                file=sys.stderr,
            )

        history = self.char_model.fit(
            X_train,
            y_train,
            batch_size=batch_size,
            epochs=effective_epochs,
            validation_data=(X_val, y_val),
            verbose=1,
            callbacks=callbacks,
        )

        elapsed_time = time.time() - start_time

        return {
            "success": True,
            "vocab_size": vocab_size,
            "sequences": len(sequences),
            "epochs_completed": len(history.history["loss"]),
            "final_loss": float(history.history["loss"][-1]),
            "final_val_loss": float(history.history["val_loss"][-1]),
            "training_time_seconds": elapsed_time,
            "time_limit_reached": time_limit_seconds is not None and elapsed_time >= time_limit_seconds,
        }

    def _train_word_model(
        self, text: str, epochs: int, continue_training: bool, time_limit_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Train word-level model
        
        Args:
            text: Training text
            epochs: Number of epochs (may be limited by time)
            continue_training: Whether to continue from existing model
            time_limit_seconds: Maximum training time in seconds (None = no limit)
        """
        sequence_length = self.config.get("training", {}).get("sequence_length", 100)
        start_time = time.time()
        
        # Create sequences
        sequences, targets = NeuralTextGeneratorData.create_word_sequences(
            text, sequence_length=sequence_length
        )

        if not sequences:
            return {"success": False, "error": "No sequences created"}

        # Build vocabulary
        self.word_vocab, self.word_vocab_reverse = (
            NeuralTextGeneratorData.build_word_vocabulary(text, min_frequency=2)
        )
        vocab_size = len(self.word_vocab)
        
        # Save vocabulary immediately so it's available even if training is interrupted
        try:
            word_meta_path = self.model_dir / "word_model.json"
            metadata = {
                "vocab": self.word_vocab,
                "vocab_reverse": self.word_vocab_reverse,
                "config": self.config.get("word_model", {}),
            }
            with open(word_meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            print(
                f"[NeuralTextGenerator] Warning: Could not save vocabulary: {e}",
                file=sys.stderr,
            )

        # Convert to arrays
        X, y = NeuralTextGeneratorData.sequences_to_arrays_word(
            sequences, targets, self.word_vocab
        )

        # Split into train/validation
        val_split = self.config.get("training", {}).get("validation_split", 0.2)
        split_idx = int(len(X) * (1 - val_split))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        # Build or load model
        if continue_training and self.word_model is None:
            self._load_model({"model_type": "word"})

        if self.word_model is None:
            word_config = self.config.get("word_model", {})
            self.word_model = self._build_word_model(
                vocab_size=vocab_size,
                embedding_dim=word_config.get("embedding_size", 256),
                hidden_size=word_config.get("hidden_size", 512),
                num_layers=word_config.get("num_layers", 2),
                dropout=word_config.get("dropout", 0.2),
            )

        # Compile model
        learning_rate = self.config.get("training", {}).get("learning_rate", 0.001)
        self.word_model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
        )

        # Train with time limit support
        batch_size = self.config.get("training", {}).get("batch_size", 64)
        
        # Custom callback for time-based training and checkpoint saving
        class TrainingCallback(keras.callbacks.Callback):
            def __init__(self, time_limit: Optional[float], start_time: float, model_dir: Path, model_type: str):
                self.time_limit = time_limit
                self.start_time = start_time
                self.should_stop = False
                self.model_dir = model_dir
                self.model_type = model_type

            def on_epoch_end(self, epoch, logs=None):
                # Check time limit
                if self.time_limit:
                    elapsed = time.time() - self.start_time
                    if elapsed >= self.time_limit:
                        print(
                            f"\n[NeuralTextGenerator] Time limit reached ({elapsed:.1f}s), stopping training",
                            file=sys.stderr,
                        )
                        self.model.stop_training = True
                        self.should_stop = True
                
                # Save checkpoint after each epoch
                try:
                    checkpoint_path = self.model_dir / "checkpoints" / f"{self.model_type}_model_epoch_{epoch+1}.h5"
                    self.model.save(checkpoint_path)
                    
                    # Also save as latest model (for easy loading after interruption)
                    latest_path = self.model_dir / f"{self.model_type}_model_latest.h5"
                    self.model.save(latest_path)
                    
                    print(
                        f"[NeuralTextGenerator] Checkpoint saved: epoch {epoch+1}",
                        file=sys.stderr,
                    )
                except Exception as e:
                    print(
                        f"[NeuralTextGenerator] Warning: Could not save checkpoint: {e}",
                        file=sys.stderr,
                    )

        callbacks = []
        callbacks.append(TrainingCallback(time_limit_seconds, start_time, self.model_dir, "word"))
        
        # Adjust epochs if time limit is very short
        effective_epochs = epochs
        if time_limit_seconds:
            # Estimate time per epoch (rough estimate: 1 epoch per 30 seconds for small models)
            estimated_epoch_time = 30.0
            max_epochs_by_time = int(time_limit_seconds / estimated_epoch_time) + 1
            effective_epochs = min(epochs, max_epochs_by_time)
            print(
                f"[NeuralTextGenerator] Time limit: {time_limit_seconds:.1f}s, "
                f"adjusting to {effective_epochs} epochs max",
                file=sys.stderr,
            )

        history = self.word_model.fit(
            X_train,
            y_train,
            batch_size=batch_size,
            epochs=effective_epochs,
            validation_data=(X_val, y_val),
            verbose=1,
            callbacks=callbacks,
        )

        elapsed_time = time.time() - start_time

        return {
            "success": True,
            "vocab_size": vocab_size,
            "sequences": len(sequences),
            "epochs_completed": len(history.history["loss"]),
            "final_loss": float(history.history["loss"][-1]),
            "final_val_loss": float(history.history["val_loss"][-1]),
            "training_time_seconds": elapsed_time,
            "time_limit_reached": time_limit_seconds is not None and elapsed_time >= time_limit_seconds,
        }

    def _build_character_model(
        self,
        vocab_size: int,
        embedding_dim: int = 128,
        hidden_size: int = 256,
        num_layers: int = 2,
        dropout: float = 0.2,
    ):
        """Build character-level LSTM model"""
        model = keras.Sequential()
        model.add(layers.Embedding(vocab_size, embedding_dim))
        
        for i in range(num_layers):
            return_sequences = i < num_layers - 1
            model.add(
                layers.LSTM(
                    hidden_size,
                    return_sequences=return_sequences,
                    dropout=dropout,
                    recurrent_dropout=dropout,
                )
            )
        
        model.add(layers.Dense(vocab_size, activation="softmax"))
        return model

    def _build_word_model(
        self,
        vocab_size: int,
        embedding_dim: int = 256,
        hidden_size: int = 512,
        num_layers: int = 2,
        dropout: float = 0.2,
    ):
        """Build word-level LSTM model"""
        model = keras.Sequential()
        model.add(layers.Embedding(vocab_size, embedding_dim))
        
        for i in range(num_layers):
            return_sequences = i < num_layers - 1
            model.add(
                layers.LSTM(
                    hidden_size,
                    return_sequences=return_sequences,
                    dropout=dropout,
                    recurrent_dropout=dropout,
                )
            )
        
        model.add(layers.Dense(vocab_size, activation="softmax"))
        return model

    def _generate_text(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate text from a prompt
        
        Args:
            params:
                - prompt: Starting text/prompt
                - model_type: "character" or "word" (default from config)
                - max_length: Maximum length to generate (default: 500)
                - temperature: Sampling temperature (default: 0.7)
                - voice_context: Optional voice context for style adaptation
        
        Returns:
            Generated text
        """
        prompt = params.get("prompt", "")
        model_type = params.get(
            "model_type",
            self.config.get("generation", {}).get("default_model", "character"),
        )
        max_length = params.get(
            "max_length",
            self.config.get("generation", {}).get("max_length", 500),
        )
        temperature = params.get(
            "temperature",
            self.config.get("generation", {}).get("temperature", 0.7),
        )
        voice_context = params.get("voice_context", {})

        # Adjust temperature based on voice context if provided
        if voice_context:
            tone = voice_context.get("tone", "neutral")
            if tone == "creative":
                temperature = min(1.2, temperature * 1.2)
            elif tone == "formal":
                temperature = max(0.5, temperature * 0.8)

        if model_type == "character":
            return self._generate_character_text(prompt, max_length, temperature)
        elif model_type == "word":
            return self._generate_word_text(prompt, max_length, temperature)
        else:
            return {"success": False, "error": f"Unknown model type: {model_type}"}

    def _generate_character_text(
        self, prompt: str, max_length: int, temperature: float
    ) -> Dict[str, Any]:
        """Generate text using character-level model"""
        if self.char_model is None or self.char_vocab is None:
            # Try to load model
            load_result = self._load_model({"model_type": "character"})
            if not load_result.get("success"):
                return {
                    "success": False,
                    "error": "Character model not trained. Train first with train_model operation.",
                }

        if self.char_model is None:
            return {"success": False, "error": "Character model not available"}

        # Convert prompt to sequence
        sequence_length = self.config.get("training", {}).get("sequence_length", 100)
        prompt_seq = [self.char_vocab.get(c, 0) for c in prompt[-sequence_length:]]
        
        # Pad if needed
        if len(prompt_seq) < sequence_length:
            prompt_seq = [0] * (sequence_length - len(prompt_seq)) + prompt_seq

        generated = prompt
        current_seq = prompt_seq.copy()

        for _ in range(max_length):
            # Predict next character
            input_array = np.array([current_seq])
            predictions = self.char_model.predict(input_array, verbose=0)[0]

            # Apply temperature sampling
            if temperature != 1.0:
                predictions = np.log(predictions + 1e-8) / temperature
                predictions = np.exp(predictions)
                predictions = predictions / np.sum(predictions)

            # Sample next character
            next_char_idx = np.random.choice(len(predictions), p=predictions)
            next_char = self.char_vocab_reverse.get(next_char_idx, " ")

            generated += next_char
            current_seq = current_seq[1:] + [next_char_idx]

        return {
            "success": True,
            "text": generated,
            "model_type": "character",
            "length": len(generated),
        }

    def _generate_word_text(
        self, prompt: str, max_length: int, temperature: float
    ) -> Dict[str, Any]:
        """Generate text using word-level model"""
        if self.word_model is None or self.word_vocab is None:
            # Try to load model
            load_result = self._load_model({"model_type": "word"})
            if not load_result.get("success"):
                return {
                    "success": False,
                    "error": "Word model not trained. Train first with train_model operation.",
                }

        if self.word_model is None:
            return {"success": False, "error": "Word model not available"}

        # Convert prompt to words
        words = prompt.lower().split()
        sequence_length = self.config.get("training", {}).get("sequence_length", 100)
        unk_idx = self.word_vocab.get("<UNK>", 0)

        prompt_seq = [
            self.word_vocab.get(word, unk_idx) for word in words[-sequence_length:]
        ]

        # Pad if needed
        if len(prompt_seq) < sequence_length:
            prompt_seq = [0] * (sequence_length - len(prompt_seq)) + prompt_seq

        generated_words = words.copy()
        current_seq = prompt_seq.copy()

        for _ in range(max_length):
            # Predict next word
            input_array = np.array([current_seq])
            predictions = self.word_model.predict(input_array, verbose=0)[0]

            # Apply temperature sampling
            if temperature != 1.0:
                predictions = np.log(predictions + 1e-8) / temperature
                predictions = np.exp(predictions)
                predictions = predictions / np.sum(predictions)

            # Sample next word
            next_word_idx = np.random.choice(len(predictions), p=predictions)
            next_word = self.word_vocab_reverse.get(next_word_idx, "<UNK>")

            if next_word in ["<UNK>", "<PAD>", "<START>", "<END>"]:
                continue

            generated_words.append(next_word)
            current_seq = current_seq[1:] + [next_word_idx]

        generated_text = " ".join(generated_words)

        return {
            "success": True,
            "text": generated_text,
            "model_type": "word",
            "length": len(generated_text),
        }

    def _generate_continuation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Continue existing text
        
        Args:
            params:
                - text: Text to continue
                - model_type: "character" or "word"
                - max_length: Maximum additional length
                - temperature: Sampling temperature
        
        Returns:
            Continued text
        """
        text = params.get("text", "")
        model_type = params.get(
            "model_type",
            self.config.get("generation", {}).get("default_model", "character"),
        )
        max_length = params.get(
            "max_length",
            self.config.get("generation", {}).get("max_length", 500),
        )
        temperature = params.get(
            "temperature",
            self.config.get("generation", {}).get("temperature", 0.7),
        )

        # Use generate_text with the existing text as prompt
        return self._generate_text(
            {
                "prompt": text,
                "model_type": model_type,
                "max_length": max_length,
                "temperature": temperature,
            }
        )

    def _load_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load pre-trained model
        
        Args:
            params:
                - model_type: "character", "word", or "both"
        
        Returns:
            Load result
        """
        model_type = params.get("model_type", "both")
        results = {}

        if model_type in ["character", "both"]:
            # Try to load latest checkpoint first, then final model
            char_model_latest = self.model_dir / "char_model_latest.h5"
            char_model_path = self.model_dir / "char_model.h5"
            char_meta_path = self.model_dir / "char_model.json"

            # Try latest checkpoint first (from interrupted training)
            if char_model_latest.exists():
                try:
                    self.char_model = keras.models.load_model(char_model_latest)
                    # Try to load metadata if available
                    if char_meta_path.exists():
                        with open(char_meta_path, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                            self.char_vocab = metadata.get("vocab", {})
                            self.char_vocab_reverse = {
                                idx: char for char, idx in self.char_vocab.items()
                            }
                    else:
                        # If no metadata, try to rebuild from model (may not work)
                        print(
                            "[NeuralTextGenerator] Warning: No metadata found, model may not work correctly",
                            file=sys.stderr,
                        )
                    results["character"] = {"success": True, "source": "latest_checkpoint"}
                    self._models_loaded = True
                except Exception as e:
                    # Fall through to try final model
                    pass
            
            # Try final model if latest didn't work
            if "character" not in results and char_model_path.exists() and char_meta_path.exists():
                try:
                    self.char_model = keras.models.load_model(char_model_path)
                    with open(char_meta_path, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                        self.char_vocab = metadata.get("vocab", {})
                        self.char_vocab_reverse = {
                            idx: char for char, idx in self.char_vocab.items()
                        }
                    results["character"] = {"success": True}
                    self._models_loaded = True
                except Exception as e:
                    results["character"] = {"success": False, "error": str(e)}
            else:
                results["character"] = {
                    "success": False,
                    "error": "Model file not found",
                }

        if model_type in ["word", "both"]:
            # Try to load latest checkpoint first, then final model
            word_model_latest = self.model_dir / "word_model_latest.h5"
            word_model_path = self.model_dir / "word_model.h5"
            word_meta_path = self.model_dir / "word_model.json"

            # Try latest checkpoint first (from interrupted training)
            if word_model_latest.exists():
                try:
                    self.word_model = keras.models.load_model(word_model_latest)
                    # Try to load metadata if available
                    if word_meta_path.exists():
                        with open(word_meta_path, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                            self.word_vocab = metadata.get("vocab", {})
                            self.word_vocab_reverse = metadata.get("vocab_reverse", {})
                    else:
                        # If no metadata, try to rebuild from model (may not work)
                        print(
                            "[NeuralTextGenerator] Warning: No metadata found, model may not work correctly",
                            file=sys.stderr,
                        )
                    results["word"] = {"success": True, "source": "latest_checkpoint"}
                    self._models_loaded = True
                except Exception as e:
                    # Fall through to try final model
                    pass
            
            # Try final model if latest didn't work
            if "word" not in results and word_model_path.exists() and word_meta_path.exists():
                try:
                    self.word_model = keras.models.load_model(word_model_path)
                    with open(word_meta_path, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                        self.word_vocab = metadata.get("vocab", {})
                        self.word_vocab_reverse = metadata.get("vocab_reverse", {})
                    results["word"] = {"success": True}
                    self._models_loaded = True
                except Exception as e:
                    results["word"] = {"success": False, "error": str(e)}
            else:
                results["word"] = {"success": False, "error": "Model file not found"}

        overall_success = any(r.get("success") for r in results.values())

        return {
            "success": overall_success,
            "results": results,
        }

    def _save_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save trained model
        
        Args:
            params:
                - model_type: "character", "word", or "both"
        
        Returns:
            Save result
        """
        model_type = params.get("model_type", "both")
        results = {}

        if model_type in ["character", "both"]:
            if self.char_model is not None and self.char_vocab is not None:
                try:
                    char_model_path = self.model_dir / "char_model.h5"
                    char_meta_path = self.model_dir / "char_model.json"

                    self.char_model.save(char_model_path)
                    
                    metadata = {
                        "vocab": self.char_vocab,
                        "config": self.config.get("character_model", {}),
                    }
                    with open(char_meta_path, "w", encoding="utf-8") as f:
                        json.dump(metadata, f, indent=2)

                    results["character"] = {
                        "success": True,
                        "path": str(char_model_path),
                    }
                except Exception as e:
                    results["character"] = {"success": False, "error": str(e)}
            else:
                results["character"] = {
                    "success": False,
                    "error": "No character model to save",
                }

        if model_type in ["word", "both"]:
            if self.word_model is not None and self.word_vocab is not None:
                try:
                    word_model_path = self.model_dir / "word_model.h5"
                    word_meta_path = self.model_dir / "word_model.json"

                    self.word_model.save(word_model_path)
                    
                    metadata = {
                        "vocab": self.word_vocab,
                        "vocab_reverse": self.word_vocab_reverse,
                        "config": self.config.get("word_model", {}),
                    }
                    with open(word_meta_path, "w", encoding="utf-8") as f:
                        json.dump(metadata, f, indent=2)

                    results["word"] = {"success": True, "path": str(word_model_path)}
                except Exception as e:
                    results["word"] = {"success": False, "error": str(e)}
            else:
                results["word"] = {"success": False, "error": "No word model to save"}

        overall_success = any(r.get("success") for r in results.values())

        return {
            "success": overall_success,
            "results": results,
        }

    def _get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models"""
        info = {
            "tensorflow_available": TENSORFLOW_AVAILABLE,
            "numpy_available": NUMPY_AVAILABLE,
            "character_model_loaded": self.char_model is not None,
            "word_model_loaded": self.word_model is not None,
            "config_loaded": self._config_loaded,
        }

        if self.char_model is not None:
            info["character_model"] = {
                "vocab_size": len(self.char_vocab) if self.char_vocab else 0,
                "model_summary": str(self.char_model.summary()) if hasattr(self.char_model, 'summary') else "N/A",
            }

        if self.word_model is not None:
            info["word_model"] = {
                "vocab_size": len(self.word_vocab) if self.word_vocab else 0,
                "model_summary": str(self.word_model.summary()) if hasattr(self.word_model, 'summary') else "N/A",
            }

        return {"success": True, "info": info}

