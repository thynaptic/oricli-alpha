"""
Advanced NLP Module - Sentiment analysis, topic modeling, text classification, and more
Handles advanced natural language processing tasks
"""

import json
import re
from typing import Dict, Any, List, Optional
from collections import Counter, defaultdict

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata

# Optional imports - will fail gracefully if dependencies not available
try:
    from textblob import TextBlob

    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    from nltk.tag import pos_tag

    try:
        from nltk.chunk import ne_chunk
    except ImportError:
        # Fallback for different NLTK versions
        from nltk import ne_chunk
    NLTK_AVAILABLE = True
    NLTK_CHUNK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    NLTK_CHUNK_AVAILABLE = False

try:
    from langdetect import detect, DetectorFactory

    DetectorFactory.seed = 0  # For consistent results
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

try:
    from gensim import corpora, models
    from gensim.parsing.preprocessing import STOPWORDS

    GENSIM_AVAILABLE = True
except ImportError:
    GENSIM_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.pipeline import Pipeline

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class AdvancedNLP(BaseBrainModule):
    """Advanced NLP capabilities"""

    def __init__(self):
        self._nltk_downloaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="advanced_nlp",
            version="1.0.0",
            description="Advanced NLP: sentiment analysis, topic modeling, text classification, entity extraction",
            operations=[
                "analyze_sentiment",
                "extract_topics",
                "classify_text",
                "extract_entities",
                "summarize",
                "detect_language",
                "calculate_similarity",
            ],
            dependencies=["nltk", "textblob", "gensim", "scikit-learn", "langdetect"],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize NLTK resources if available"""
        if NLTK_AVAILABLE:
            try:
                nltk.download("punkt", quiet=True)
                nltk.download("stopwords", quiet=True)
                nltk.download("averaged_perceptron_tagger", quiet=True)
                nltk.download("maxent_ne_chunker", quiet=True)
                nltk.download("words", quiet=True)
                self._nltk_downloaded = True
            except Exception:
                pass
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute NLP operations"""

        if operation == "analyze_sentiment":
            text = params.get("text", "")
            return self.analyze_sentiment(text)

        elif operation == "extract_topics":
            texts = params.get("texts", [])
            if isinstance(texts, str):
                texts = json.loads(texts) if texts.startswith("[") else [texts]
            num_topics = params.get("num_topics", 5)
            return self.extract_topics(texts, num_topics)

        elif operation == "classify_text":
            text = params.get("text", "")
            categories = params.get("categories", [])
            if isinstance(categories, str):
                categories = (
                    json.loads(categories)
                    if categories.startswith("[")
                    else categories.split(",")
                )
            return self.classify_text(text, categories)

        elif operation == "extract_entities":
            text = params.get("text", "")
            return self.extract_entities(text)

        elif operation == "summarize":
            text = params.get("text", "")
            max_sentences = params.get("max_sentences", 3)
            return self.summarize(text, max_sentences)

        elif operation == "detect_language":
            text = params.get("text", "")
            return self.detect_language(text)

        elif operation == "calculate_similarity":
            text1 = params.get("text1", "")
            text2 = params.get("text2", "")
            return self.calculate_similarity(text1, text2)

        else:
            raise ValueError(f"Unknown operation: {operation}")

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text"""
        try:
            if not text:
                return {"success": False, "error": "Text cannot be empty"}

            if TEXTBLOB_AVAILABLE:
                blob = TextBlob(text)
                polarity = blob.sentiment.polarity  # -1 to 1
                subjectivity = blob.sentiment.subjectivity  # 0 to 1

                # Classify sentiment
                if polarity > 0.1:
                    sentiment = "positive"
                elif polarity < -0.1:
                    sentiment = "negative"
                else:
                    sentiment = "neutral"

                return {
                    "success": True,
                    "result": {
                        "sentiment": sentiment,
                        "polarity": float(polarity),
                        "subjectivity": float(subjectivity),
                        "confidence": abs(polarity),
                    },
                }
            else:
                # Fallback: simple keyword-based sentiment
                positive_words = [
                    "good",
                    "great",
                    "excellent",
                    "amazing",
                    "wonderful",
                    "love",
                    "like",
                    "happy",
                    "pleased",
                ]
                negative_words = [
                    "bad",
                    "terrible",
                    "awful",
                    "hate",
                    "dislike",
                    "sad",
                    "angry",
                    "disappointed",
                ]

                text_lower = text.lower()
                positive_count = sum(1 for word in positive_words if word in text_lower)
                negative_count = sum(1 for word in negative_words if word in text_lower)

                if positive_count > negative_count:
                    sentiment = "positive"
                    polarity = 0.5
                elif negative_count > positive_count:
                    sentiment = "negative"
                    polarity = -0.5
                else:
                    sentiment = "neutral"
                    polarity = 0.0

                return {
                    "success": True,
                    "result": {
                        "sentiment": sentiment,
                        "polarity": polarity,
                        "subjectivity": 0.5,
                        "confidence": abs(polarity),
                        "note": "Using simple keyword-based analysis (install textblob for better results)",
                    },
                }
        except Exception as e:
            return {"success": False, "error": f"Sentiment analysis failed: {str(e)}"}

    def extract_topics(self, texts: List[str], num_topics: int = 5) -> Dict[str, Any]:
        """Extract topics from texts using topic modeling"""
        try:
            if not texts:
                return {"success": False, "error": "Texts list cannot be empty"}

            if GENSIM_AVAILABLE:
                # Preprocess texts
                processed_texts = []
                for text in texts:
                    # Simple tokenization and cleaning
                    words = text.lower().split()
                    words = [w for w in words if len(w) > 3 and w not in STOPWORDS]
                    processed_texts.append(words)

                if not processed_texts or not any(processed_texts):
                    return {"success": False, "error": "No valid text to process"}

                # Create dictionary and corpus
                dictionary = corpora.Dictionary(processed_texts)
                corpus = [dictionary.doc2bow(text) for text in processed_texts]

                # Run LDA
                lda_model = models.LdaModel(
                    corpus, num_topics=num_topics, id2word=dictionary, passes=10
                )

                # Extract topics
                topics = []
                for idx, topic in lda_model.print_topics(-1, num_words=5):
                    words = re.findall(r'"(\w+)"', topic)
                    topics.append(
                        {"topic_id": idx, "keywords": words, "description": topic}
                    )

                return {
                    "success": True,
                    "result": {"num_topics": len(topics), "topics": topics},
                }
            else:
                # Fallback: simple keyword frequency
                all_words = []
                for text in texts:
                    words = text.lower().split()
                    words = [w for w in words if len(w) > 4]
                    all_words.extend(words)

                word_freq = Counter(all_words)
                top_words = word_freq.most_common(num_topics * 3)

                topics = []
                for i in range(num_topics):
                    start_idx = i * 3
                    keywords = [
                        word for word, _ in top_words[start_idx : start_idx + 3]
                    ]
                    topics.append(
                        {
                            "topic_id": i,
                            "keywords": keywords,
                            "description": f"Topic {i}: {', '.join(keywords)}",
                        }
                    )

                return {
                    "success": True,
                    "result": {
                        "num_topics": len(topics),
                        "topics": topics,
                        "note": "Using simple keyword frequency (install gensim for LDA topic modeling)",
                    },
                }
        except Exception as e:
            return {"success": False, "error": f"Topic extraction failed: {str(e)}"}

    def classify_text(self, text: str, categories: List[str]) -> Dict[str, Any]:
        """Classify text into categories"""
        try:
            if not text:
                return {"success": False, "error": "Text cannot be empty"}

            if not categories:
                return {"success": False, "error": "Categories list cannot be empty"}

            # Simple keyword-based classification
            text_lower = text.lower()
            category_scores = {}

            # Category keywords (simplified - would use trained model in production)
            category_keywords = {
                "technology": [
                    "computer",
                    "software",
                    "code",
                    "programming",
                    "tech",
                    "digital",
                    "app",
                    "system",
                ],
                "science": [
                    "research",
                    "study",
                    "experiment",
                    "theory",
                    "hypothesis",
                    "data",
                    "analysis",
                ],
                "business": [
                    "company",
                    "market",
                    "sales",
                    "revenue",
                    "profit",
                    "customer",
                    "business",
                ],
                "health": [
                    "health",
                    "medical",
                    "doctor",
                    "patient",
                    "treatment",
                    "disease",
                    "medicine",
                ],
                "sports": [
                    "game",
                    "player",
                    "team",
                    "match",
                    "sport",
                    "athlete",
                    "competition",
                ],
                "politics": [
                    "government",
                    "policy",
                    "political",
                    "election",
                    "vote",
                    "law",
                    "senate",
                ],
                "entertainment": [
                    "movie",
                    "film",
                    "music",
                    "show",
                    "actor",
                    "celebrity",
                    "entertainment",
                ],
            }

            for category in categories:
                category_lower = category.lower()
                keywords = category_keywords.get(category_lower, [category_lower])
                score = sum(1 for keyword in keywords if keyword in text_lower)
                category_scores[category] = score / len(keywords) if keywords else 0

            # Find best match
            best_category = (
                max(category_scores.items(), key=lambda x: x[1])[0]
                if category_scores
                else categories[0]
            )
            confidence = category_scores.get(best_category, 0.0)

            return {
                "success": True,
                "result": {
                    "text": text[:100] + "..." if len(text) > 100 else text,
                    "category": best_category,
                    "confidence": float(confidence),
                    "all_scores": {k: float(v) for k, v in category_scores.items()},
                },
            }
        except Exception as e:
            return {"success": False, "error": f"Text classification failed: {str(e)}"}

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract named entities from text"""
        try:
            if not text:
                return {"success": False, "error": "Text cannot be empty"}

            if NLTK_AVAILABLE and NLTK_CHUNK_AVAILABLE and self._nltk_downloaded:
                tokens = word_tokenize(text)
                tagged = pos_tag(tokens)
                entities = ne_chunk(tagged, binary=False)

                people = []
                organizations = []
                locations = []

                for entity in entities:
                    if hasattr(entity, "label"):
                        if entity.label() == "PERSON":
                            people.append(" ".join([token[0] for token in entity]))
                        elif entity.label() == "ORGANIZATION":
                            organizations.append(
                                " ".join([token[0] for token in entity])
                            )
                        elif entity.label() == "GPE" or entity.label() == "LOCATION":
                            locations.append(" ".join([token[0] for token in entity]))

                return {
                    "success": True,
                    "result": {
                        "people": list(set(people)),
                        "organizations": list(set(organizations)),
                        "locations": list(set(locations)),
                        "total_entities": len(people)
                        + len(organizations)
                        + len(locations),
                    },
                }
            else:
                # Fallback: simple pattern matching
                # Capitalized words might be entities
                words = text.split()
                capitalized = [w for w in words if w[0].isupper() and len(w) > 1]

                return {
                    "success": True,
                    "result": {
                        "people": [],
                        "organizations": [],
                        "locations": [],
                        "potential_entities": list(set(capitalized))[:10],
                        "note": "Using simple pattern matching (install nltk for proper NER)",
                    },
                }
        except Exception as e:
            return {"success": False, "error": f"Entity extraction failed: {str(e)}"}

    def summarize(self, text: str, max_sentences: int = 3) -> Dict[str, Any]:
        """Summarize text"""
        try:
            if not text:
                return {"success": False, "error": "Text cannot be empty"}

            if NLTK_AVAILABLE and self._nltk_downloaded:
                sentences = sent_tokenize(text)
            else:
                # Simple sentence splitting
                sentences = re.split(r"[.!?]+", text)
                sentences = [s.strip() for s in sentences if s.strip()]

            if len(sentences) <= max_sentences:
                summary = " ".join(sentences)
            else:
                # Take first and last sentences
                summary_sentences = sentences[:max_sentences]
                summary = ". ".join(summary_sentences) + "."

            return {
                "success": True,
                "result": {
                    "summary": summary,
                    "original_length": len(text),
                    "summary_length": len(summary),
                    "compression_ratio": len(summary) / len(text) if text else 0,
                },
            }
        except Exception as e:
            return {"success": False, "error": f"Summarization failed: {str(e)}"}

    def detect_language(self, text: str) -> Dict[str, Any]:
        """Detect language of text"""
        try:
            if not text:
                return {"success": False, "error": "Text cannot be empty"}

            if LANGDETECT_AVAILABLE:
                language = detect(text)
                return {
                    "success": True,
                    "result": {
                        "language": language,
                        "confidence": 1.0,  # langdetect doesn't provide confidence
                    },
                }
            else:
                # Fallback: simple heuristics
                # Check for common language patterns
                text_lower = text.lower()
                if any(
                    word in text_lower
                    for word in ["the", "and", "is", "are", "was", "were"]
                ):
                    language = "en"
                elif any(
                    word in text_lower for word in ["el", "la", "de", "que", "y", "en"]
                ):
                    language = "es"
                elif any(
                    word in text_lower
                    for word in ["le", "de", "et", "est", "un", "une"]
                ):
                    language = "fr"
                else:
                    language = "unknown"

                return {
                    "success": True,
                    "result": {
                        "language": language,
                        "confidence": 0.5,
                        "note": "Using simple heuristics (install langdetect for better results)",
                    },
                }
        except Exception as e:
            return {"success": False, "error": f"Language detection failed: {str(e)}"}

    def calculate_similarity(self, text1: str, text2: str) -> Dict[str, Any]:
        """Calculate similarity between two texts"""
        try:
            if not text1 or not text2:
                return {"success": False, "error": "Both texts must be provided"}

            if SKLEARN_AVAILABLE:
                vectorizer = TfidfVectorizer()
                tfidf_matrix = vectorizer.fit_transform([text1, text2])
                similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][
                    0
                ]

                return {
                    "success": True,
                    "result": {
                        "similarity": float(similarity),
                        "similarity_percent": float(similarity * 100),
                    },
                }
            else:
                # Fallback: simple word overlap
                words1 = set(text1.lower().split())
                words2 = set(text2.lower().split())

                intersection = words1 & words2
                union = words1 | words2

                similarity = len(intersection) / len(union) if union else 0.0

                return {
                    "success": True,
                    "result": {
                        "similarity": float(similarity),
                        "similarity_percent": float(similarity * 100),
                        "note": "Using simple word overlap (install scikit-learn for TF-IDF similarity)",
                    },
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Similarity calculation failed: {str(e)}",
            }
