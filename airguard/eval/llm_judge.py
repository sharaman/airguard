import json

from langchain_groq import ChatGroq

from airguard.config import GROQ_API_KEY, LLM_MODEL
from airguard.eval.benchmark import TEST_CASES, build_test_state
from airguard.graph.nodes import report_node

judge_llm = ChatGroq(model=LLM_MODEL, temperature=0, api_key=GROQ_API_KEY)

JUDGE_PROMPT = """\
Оцени качество алерта о качестве воздуха.

Данные воздуха: {air_data}
Профиль пользователя: {user_profile}
Сгенерированный алерт: {alert_message}

Оцени по критериям (каждый: pass/fail + объяснение):
1. Фактическая корректность — алерт соответствует данным?
2. Полезность — есть конкретные рекомендации?
3. Тон — не паникёрский и не слишком мягкий для ситуации?
4. Краткость — не более 10 строк?

Ответь ТОЛЬКО в JSON без markdown-разметки:
{{"criteria": {{"accuracy": "pass", "usefulness": "pass", "tone": "pass", "brevity": "pass"}}, "overall": "pass", "comment": "..."}}
"""


def judge_alert(air_data: dict, user_profile: dict, alert_message: str) -> dict:
    response = judge_llm.invoke(
        JUDGE_PROMPT.format(
            air_data=air_data,
            user_profile=user_profile,
            alert_message=alert_message,
        )
    )
    text = response.content.strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])


def run_llm_eval(sample_size: int = 5):
    cases = TEST_CASES[:sample_size]
    results = []
    passed = 0

    for tc in cases:
        state = build_test_state(tc["input"])
        output = report_node(state)
        verdict = judge_alert(
            tc["input"]["air_data"],
            tc["input"]["user_profile"],
            output["alert_message"],
        )
        is_pass = verdict.get("overall") == "pass"
        if is_pass:
            passed += 1
        results.append({"id": tc["id"], "verdict": verdict})
        status = "PASS" if is_pass else "FAIL"
        print(f"[{status}] {tc['id']}: {verdict.get('comment', '')}")

        criteria = verdict.get("criteria", {})
        failed_criteria = [k for k, v in criteria.items() if v != "pass"]
        if failed_criteria:
            print(f"       failed: {', '.join(failed_criteria)}")

    print(f"\n{passed}/{len(cases)} passed (LLM judge)")
    return results


if __name__ == "__main__":
    run_llm_eval()
