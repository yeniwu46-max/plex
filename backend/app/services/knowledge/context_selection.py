"""Evidence diversity without changing candidate relevance or source permissions."""
from .providers.embedding import cosine
from .text_utils import content_hash, tokenize


def evidence_key(content):
    # Even unfenced Python may carry meaningful indentation and string spaces.
    # Only line-ending conventions are canonicalized for exact copy detection.
    return content_hash((content or '').replace('\r\n', '\n'))


def select_context(ranked, *, limit, per_document, config):
    if not ranked:
        return []
    deduplicate = config.get('deduplicate_exact', True)
    use_mmr = config.get('mmr_enabled', False)
    weight = max(0.0, min(1.0, float(config.get('mmr_relevance_weight', .75))))
    remaining, keys = [], set()
    for row in ranked:
        key = evidence_key(row.content)
        if deduplicate and key in keys:
            continue
        keys.add(key)
        remaining.append(row)
    selected, doc_counts = [], {}
    tokens = {r.chunk_id: set(tokenize(r.content, drop_stopwords=False)) for r in remaining}
    maximum = max((r.final_score for r in remaining), default=1) or 1

    def similarity(left, right):
        if left.selection_vector and right.selection_vector and len(left.selection_vector) == len(right.selection_vector):
            return max(0.0, min(1.0, cosine(left.selection_vector, right.selection_vector)))
        a, b = tokens[left.chunk_id], tokens[right.chunk_id]
        return len(a & b) / max(1, len(a | b))

    while remaining and len(selected) < limit:
        eligible = [r for r in remaining if doc_counts.get(r.document_id, 0) < per_document]
        if not eligible:
            break
        scores = {}
        for row in eligible:
            redundant = max((similarity(row, picked) for picked in selected), default=0.) if use_mmr else 0.
            score = weight * row.final_score / maximum - (1 - weight) * redundant if use_mmr else row.final_score
            scores[row.chunk_id] = (score, redundant)
        # Input is ordered by relevance; ties retain that order deterministically.
        chosen = max(eligible, key=lambda r: scores[r.chunk_id][0])
        score, redundant = scores[chosen.chunk_id]
        chosen.score_breakdown.update(selection_score=round(score, 4), redundancy_similarity=round(redundant, 4))
        selected.append(chosen)
        doc_counts[chosen.document_id] = doc_counts.get(chosen.document_id, 0) + 1
        remaining.remove(chosen)
    return selected
