"""
BERT Intent Classifier — مصنف النوايا الذكي باستخدام تمثيلات BERT الدلالية
يقوم بتصنيف استفسارات المستخدمين إلى 7 نوايا رئيسية لتوجيهها بدقة للمحرك المتخصص:
1. catalog_query     -> DeterministicCatalogEngine
2. drug_interaction  -> InteractionGuard
3. emergency         -> EscalationEngine
4. price_calc        -> DeterministicMathEngine
5. general_qa        -> Hybrid RAG Pipeline
6. greeting          -> Direct Conversational Response
7. out_of_scope      -> Security & Scope Guard
"""

import time
import numpy as np
from typing import Optional, Dict, Any, List

# عينات تدريبية معيارية لكل نية (Intent Prototypes / Anchors)
CLINICAL_INTENT_ANCHORS: Dict[str, List[str]] = {
    "catalog_query": [
        "عايز أدوية حساسية الصدر",
        "عندكم دواء للضغط أو السكر في الصيدلية؟",
        "أدوية المسكنات المتاحة للبيع",
        "قائمة أدوية المضاد الحيوي المتوفرة",
        "هل متوفر عندكم بروفين أو بنادول؟",
        "do you have diabetes medications or insulin?",
        "show me available pain relief drugs in catalog",
        "are there any antibiotics available?"
    ],
    "drug_interaction": [
        "ينفع آخد بروفين مع كاتافلام؟",
        "هل يتعارض كونكور مع ديوفان؟",
        "هل فيه تفاعل خطير بين الأسبرين والبروفين؟",
        "هل أدوية الغدة تتعارض مع الكالسيوم؟",
        "هل مسموح أخد كابوتن مع مسكنات الروماتيزم؟",
        "can I take ibuprofen together with capoten?",
        "is there a drug conflict between concor and brufen?",
        "drug interaction between metformin and nsaids"
    ],
    "emergency": [
        "مش قادر أتنفس وبموت الحقوني بسرعة",
        "المريض بلع شريط أقراص كامل ومغمى عليه",
        "نزيف حاد مستمر مع هبوط حاد في الضغط",
        "حساسية مفرطة وتورم في الحلق واللسان طوارئ",
        "طفل شرب دواء بالغين بالخطأ وفاقد الوعي",
        "severe acute chest pain cardiac emergency",
        "cannot breathe anaphylaxis emergency ambulance",
        "poisoning overdose unconscious patient"
    ],
    "price_calc": [
        "سعر 3 علب أوجمنتين مع كود خصم CARE15",
        "احسبلي تمن علبتين بنادول مع علبة فيتامين",
        "علبتين كونكور 5 بكام بعد الخصم الإجمالي؟",
        "احسب التكلفة الإجمالية لطلبيتي مع كود التخفيض",
        "calculate total order cost with 15 percent discount",
        "how much for 3 packs of lipitor after coupon"
    ],
    "general_qa": [
        "إيه هي فوائد فيتامين C وأضراره وطريقة استعماله؟",
        "كيف يعمل دواء كونكور على خفض ضغط الدم؟",
        "ما هي الآثار الجانبية الشائعة للميتفورمين؟",
        "أفضل وقت لتناول أدوية الغدة الدرقية التروكسين",
        "ما هو الفرق بين الباراسيتامول والإيبوبروفين؟",
        "what are the contraindications of lipitor?",
        "how does beta blocker mechanism work in the body?",
        "recommended daily dose for zinc supplements"
    ],
    "greeting": [
        "السلام عليكم ورحمة الله وبركاته",
        "صباح الخير يا دكتور الصيدلية",
        "مساء الخير ازيك عامل ايه",
        "أهلاً وسهلاً مين معايا؟",
        "شكراً جزيلاً وجزاك الله خيراً",
        "hello good morning pharmacy assistant",
        "hi who are you and how can you help?",
        "thank you very much have a nice day"
    ],
    "out_of_scope": [
        "إيه أخبار الطقس ودرجات الحرارة النهاردة؟",
        "مين فاز في ماتش الأهلي والزمالك في الدوري؟",
        "عايز اشتري موبايل سامسونج أو لابتوب",
        "كيف أصلح عطل في محرك السيارة؟",
        "اكتبلي كود بايثون لتصميم موقع",
        "who is the president of france?",
        "what is the capital of australia?",
        "tell me a joke about programming"
    ]
}


class BERTIntentClassifier:
    """
    مصنف النوايا الدلالي فائق السرعة المبني على BERT.
    يستخدم متجهات التضمين للـ Anchors لحساب التشابه الدلالي بدقة فائقة.
    """
    _instance = None
    _centroids: Dict[str, np.ndarray] = {}
    _is_initialized = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def initialize(cls, encoder=None):
        """تهيئة متجهات المراكز (Centroids) مسبقاً لضمان زمن استجابة < 2ms"""
        if cls._is_initialized and cls._centroids:
            return

        if encoder is None:
            from app.domains.ai.service import _get_encoder
            encoder = _get_encoder()

        for intent, samples in CLINICAL_INTENT_ANCHORS.items():
            embeddings = encoder.encode(samples, normalize_embeddings=True)
            centroid = np.mean(embeddings, axis=0)
            norm = np.linalg.norm(centroid)
            if norm > 0:
                cls._centroids[intent] = centroid / norm
            else:
                cls._centroids[intent] = centroid

        cls._is_initialized = True

    @classmethod
    def classify(
        cls,
        query: str,
        query_vector: Optional[List[float]] = None,
        encoder=None
    ) -> Dict[str, Any]:
        """
        تصنيف استفسار المستخدم وحساب درجات الثقة لكل نية.
        """
        t0 = time.time()
        cls.initialize(encoder)

        if query_vector is None:
            if encoder is None:
                from app.domains.ai.service import _get_encoder
                encoder = _get_encoder()
            q_vec = encoder.encode([query], normalize_embeddings=True)[0]
        else:
            q_vec = np.array(query_vector)
            norm = np.linalg.norm(q_vec)
            if norm > 0:
                q_vec = q_vec / norm

        scores: Dict[str, float] = {}
        for intent, centroid in cls._centroids.items():
            dot = float(np.dot(q_vec, centroid))
            scores[intent] = round(max(0.0, min(1.0, dot)), 4)

        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_intent, top_score = sorted_intents[0]
        second_intent, second_score = sorted_intents[1] if len(sorted_intents) > 1 else ("", 0.0)

        latency_ms = int((time.time() - t0) * 1000)

        return {
            "predicted_intent": top_intent,
            "confidence": top_score,
            "margin": round(top_score - second_score, 4),
            "all_scores": scores,
            "is_confident": bool(top_score >= 0.50),
            "model_name": "paraphrase-multilingual-MiniLM-L12-v2 (BERT)",
            "latency_ms": latency_ms
        }
