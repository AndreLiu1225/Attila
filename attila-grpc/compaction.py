import json

from harness.harness import MODEL, client

CONTEXT_WINDOW = 131_072
OUTPUT_RESERVE = 480
INPUT_BUDGET = CONTEXT_WINDOW - OUTPUT_RESERVE - 1_000
TAIL_BUDGET = 8_000
COMPACT_AT = 8_000
MAX_USER_PROMPT_TOKENS = 4_000

SUMMARY_PROMPT = (
    "Summarize the transcript into state another model can continue from. "
    "Use these sections: Goal, Constraints, Progress, Findings, Decisions, Next step. "
    "Keep command names and their results. Mark failed commands as failed. "
    "Do not answer the user."
)


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 3)


def estimate_messages(messages) -> int:
    total = 0
    for message in messages:
        total += estimate_tokens(message.get("content") or "")
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            total += estimate_tokens(function.get("name") or "")
            total += estimate_tokens(function.get("arguments") or "")
    return total


def decode_message(sender, content, message):
    if message is not None:
        return message if isinstance(message, dict) else json.loads(message)
    if sender == "client":
        return {"role": "user", "content": content}
    if sender == "agent":
        return {"role": "assistant", "content": content}
    return None


def load_rows(conn, db_lock, conversation_id):
    with db_lock, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, sender, content, message
            FROM messages
            WHERE conversation_id = %s
            ORDER BY created_at, id
            """,
            (conversation_id,),
        )
        rows = []
        for message_id, sender, content, message in cur.fetchall():
            decoded = decode_message(sender, content, message)
            if decoded is not None:
                rows.append((message_id, decoded))
        return rows


def load_checkpoint(conn, db_lock, conversation_id):
    with db_lock, conn.cursor() as cur:
        cur.execute(
            """
            SELECT summary, first_kept_id
            FROM checkpoints
            WHERE conversation_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (conversation_id,),
        )
        return cur.fetchone()


def project(rows, checkpoint):
    summary = None
    kept = rows
    if checkpoint is not None:
        summary, first_kept_id = checkpoint
        kept = [row for row in rows if row[0] >= first_kept_id]
    messages = []
    if summary:
        messages.append({
            "role": "system",
            "content": "Conversation checkpoint:\n" + summary,
        })
    messages.extend(message for _, message in kept)
    return messages


def split_turns(rows):
    prefix = []
    turns = []
    current = None
    for row in rows:
        if row[1].get("role") == "user":
            if current:
                turns.append(current)
            current = [row]
        elif current is None:
            prefix.append(row)
        else:
            current.append(row)
    if current:
        turns.append(current)
    return prefix, turns


def choose_tail(turns):
    kept = []
    used = 0
    for turn in reversed(turns):
        cost = estimate_messages([message for _, message in turn])
        if kept and used + cost > TAIL_BUDGET:
            break
        kept.append(turn)
        used += cost
    kept.reverse()
    return kept


def serialize(messages):
    lines = []
    for message in messages:
        content = (message.get("content") or "")[:2000]
        lines.append(f"[{message.get('role')}] {content}")
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            arguments = function.get("arguments") or ""
            lines.append(f"[tool_call] {function.get('name')} {arguments[:500]}")
    return "\n".join(lines)


def summarize(previous_summary, dropped):
    parts = []
    if previous_summary:
        parts.append("Previous checkpoint:\n" + previous_summary)
    if dropped:
        parts.append("Turns to fold in:\n" + serialize(dropped))
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": "\n\n".join(parts)},
        ],
        max_completion_tokens=OUTPUT_RESERVE,
        reasoning_effort="low",
    )
    return completion.choices[0].message.content or ""


def save_checkpoint(conn, db_lock, conversation_id, summary, first_kept_id):
    with db_lock, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO checkpoints (conversation_id, summary, first_kept_id)
            VALUES (%s, %s, %s)
            """,
            (conversation_id, summary, first_kept_id),
        )


def compact(conn, db_lock, conversation_id, rows, checkpoint):
    visible = rows
    previous_summary = None
    if checkpoint is not None:
        previous_summary, first_kept_id = checkpoint
        visible = [row for row in rows if row[0] >= first_kept_id]

    prefix, turns = split_turns(visible)
    if not turns:
        return project(rows, checkpoint), checkpoint

    kept_turns = choose_tail(turns)
    dropped_turns = turns[: len(turns) - len(kept_turns)]
    dropped_rows = prefix + [row for turn in dropped_turns for row in turn]
    if not dropped_rows:
        return project(rows, checkpoint), checkpoint

    summary = summarize(previous_summary, [message for _, message in dropped_rows])
    first_kept_id = kept_turns[0][0][0]
    save_checkpoint(conn, db_lock, conversation_id, summary, first_kept_id)
    checkpoint = (summary, first_kept_id)
    return project(rows, checkpoint), checkpoint


def prepare_context(conn, db_lock, conversation_id, prompt):
    """Return (messages, error). messages includes the new user prompt."""
    if estimate_tokens(prompt) > MAX_USER_PROMPT_TOKENS:
        return None, (
            f"Prompt is too long. Cut it down below {MAX_USER_PROMPT_TOKENS} tokens."
        )

    rows = load_rows(conn, db_lock, conversation_id)
    checkpoint = load_checkpoint(conn, db_lock, conversation_id)
    projected = project(rows, checkpoint)
    new_user = {"role": "user", "content": prompt}

    if estimate_messages(projected + [new_user]) > COMPACT_AT:
        projected, _checkpoint = compact(conn, db_lock, conversation_id, rows, checkpoint)

    if estimate_messages(projected + [new_user]) > INPUT_BUDGET:
        return None, (
            "Prompt plus the remaining conversation is too long. Cut the prompt down."
        )

    return projected + [new_user], None
