# -*- coding: utf-8 -*-
"""
Two-Stage Hybrid Retrieval (BM25 Lexical + BERT Dense) Module
AI-COS Pharmacy System
"""

import re
from typing import List, Dict, Any
from app.domains.ai.nlp_processor import normalize_arabic, light_stem

class BM25LexicalRetriever:
    @classmethod
    def score_chunk(cls, query: str, chunk_content: str) -> float:
        norm_query = normalize_arabic(query.lower())
        norm_chunk = normalize_arabic(chunk_content.lower())
        
        query_words = [light_stem(w) for w in norm_query.split() if len(w) > 1]
        chunk_words = [light_stem(w) for w in norm_chunk.split() if len(w) > 1]
        
        if not query_words or not chunk_words:
            return 0.0
            
        exact_boost = 0.0
        query_numbers = re.findall(r'\d+', query)
        chunk_numbers = re.findall(r'\d+', chunk_content)
        common_numbers = set(query_numbers).intersection(set(chunk_numbers))
        if common_numbers:
            exact_boost += 0.3 * len(common_numbers)
            
        matched_count = 0
        for qw in query_words:
            if qw in chunk_words or any(qw in cw for cw in chunk_words):
                matched_count += 1
                
        lexical_score = (matched_count / len(query_words)) + exact_boost
        return min(1.0, lexical_score)

    @classmethod
    def hybrid_rerank(
        cls,
        query: str,
        dense_chunks: List[Dict[str, Any]],
        weight_dense: float = 0.6,
        weight_lexical: float = 0.4
    ) -> List[Dict[str, Any]]:
        reranked = []
        for chunk in dense_chunks:
            content = chunk.get('content', '')
            dense_sim = float(chunk.get('similarity', 0.5))
            lex_score = cls.score_chunk(query, content)
            
            hybrid_score = (weight_dense * dense_sim) + (weight_lexical * lex_score)
            
            item = dict(chunk)
            item['dense_similarity'] = dense_sim
            item['lexical_score'] = lex_score
            item['hybrid_score'] = hybrid_score
            reranked.append(item)
            
        reranked.sort(key=lambda x: x['hybrid_score'], reverse=True)
        return reranked
