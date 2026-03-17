import subprocess
import re



def get_confidence_label(score):

    if score >= 0.60:
        return "High Confidence"

    elif score >= 0.35:
        return "Medium Confidence"

    else:
        return "Low Confidence"
    

def build_prompt(question, contexts):
    context_text = "\n\n".join(
        f"[Source: {c['filename']} | Page {c['page']}]\n{c['content']}"
        for c in contexts
    )

    prompt = f"""
You are an AI assistant. Answer the question strictly using the context below.
If the answer is not present, say "Answer not found in the provided documents."

Context:
{context_text}

Question:
{question}

Answer:
"""
    return prompt.strip()


def ask_llm(prompt, model="llama3"):
    process = subprocess.Popen(
        ["ollama", "run", model],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    output, _ = process.communicate(prompt)
    return output.strip()

def is_entity_query(query):
    words = query.strip().split()
    return len(words) <= 3 and not query.strip().endswith("?")

def extract_answer_from_chunks(chunks, max_chars=600):
    seen = set()
    answer_parts = []

    for c in chunks:
        text = c["content"].strip()
        if text and text not in seen:
            answer_parts.append(text)
            seen.add(text)

        if sum(len(a) for a in answer_parts) > max_chars:
            break

    return "\n\n".join(answer_parts)

def clean_chunk_text(text, max_chars=400):

    # remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # remove URLs
    text = re.sub(r"http\S+|www\S+", "", text)

    # remove emails
    text = re.sub(r"\S+@\S+", "", text)

    # limit length
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "..."

    return text

def keyword_present(text, keyword):
    return keyword.lower() in text.lower()

def looks_like_definition(text):
    patterns = [
        " is the ",
        " refers to ",
        " is defined as ",
        " means "
    ]
    text = text.lower()
    return any(p in text for p in patterns)

def extract_best_sentence(text, keyword):

    sentences = re.split(r'[.?!]', text)

    keyword = keyword.lower()

    for s in sentences:
        if keyword in s.lower():
            return s.strip()

    # fallback: return first sentence
    if sentences:
        return sentences[0].strip()

    return text
def build_extractive_answer(
    ranked_chunks,
    query_word,
    question_type,
    max_items=3
):
    answer_points = []
    source_info = []

    query_word_lower = query_word.lower()
    count = 1

    for chunk, score in ranked_chunks:

        raw_text = chunk["content"]

        # ⛔ keyword must exist
        if not keyword_present(raw_text, query_word):
            continue

        # ⛔ definition questions must look like definitions
        if question_type == "definition":
            if not looks_like_definition(raw_text):
                continue

        # Clean the chunk
        clean_text = clean_chunk_text(raw_text)

        if not clean_text:
            continue

        # Extract best sentence
        best_sentence = extract_best_sentence(clean_text, query_word)

        if not best_sentence:
            continue

        # Highlight keyword
        highlighted = re.sub(
            rf"\b({re.escape(query_word_lower)})\b",
            r"**\1**",
            best_sentence,
            flags=re.IGNORECASE
        )

        answer_points.append(f"{count}. {highlighted}")

        source_info.append({
            "filename": chunk["filename"],
            "page": int(chunk["page"]),
            "score": float(round(score * 100, 1))
        })

        count += 1

        if count > max_items:
            break

    return answer_points, source_info

def build_fallback_answer(query):
    return (
        f"The topic '{query}' was not found in the provided documents.\n\n"
        f"Basic explanation:\n"
        f"{query} refers to a general concept commonly used in its domain."
    )


def summarize_chunks(chunks, max_sentences=3):
    text = " ".join(c["content"] for c in chunks[:5])

    sentences = re.split(r'(?<=[.!?]) +', text)

    summary = " ".join(sentences[:max_sentences])

    return summary