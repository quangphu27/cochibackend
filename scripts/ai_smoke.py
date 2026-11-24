"""Smoke-test AI vocab lab, THPT mock, TTS."""
import traceback
from app import create_app
from app.services.text_vocab_service import TextVocabService
from app.services.thpt_mock_service import ThptMockService, LEVELS
from app.services.tts_service import TtsService
from app.services.ai_service import AI_TOOLS

SAMPLE = (
    "Climate change is one of the most significant challenges of our time. "
    "Rising temperatures affect agriculture, health, and coastal communities around the world. "
    "Although many countries have promised to reduce emissions, progress has been uneven. "
    "Scientists argue that we need both technological innovation and changes in everyday behaviour. "
    "Renewable energy and better public transport can help. "
    "Young people are increasingly involved in environmental campaigns."
)

results = []


def ok(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    results.append((status, name, detail))
    print(status, name, detail)


def main():
    app = create_app()
    with app.app_context():
        ok("ai_tools_keys", len(AI_TOOLS) >= 1, ",".join(list(AI_TOOLS.keys())[:10]))

        try:
            svc = TextVocabService()
            data, status = svc.analyze(SAMPLE, "B1", "gemini")
            hard = (data or {}).get("hard_words") or []
            ok(
                "vocab_analyze",
                status == 200 and len(hard) >= 1,
                f"status={status} hard={len(hard)} words={data.get('word_count')}",
            )
            words = [w.get("word") for w in hard[:8] if w.get("word")]
            pdata, pstatus = svc.practice(SAMPLE, "B1", "summary", words, "gemini")
            ok(
                "vocab_practice_summary",
                pstatus == 200 and isinstance(pdata, dict) and "error" not in pdata,
                f"status={pstatus} keys={list(pdata.keys())[:8] if isinstance(pdata, dict) else pdata}",
            )
            qdata, qstatus = svc.practice(SAMPLE, "B1", "vocab_quiz", words, "gemini")
            qs = (qdata or {}).get("questions") or (qdata or {}).get("items") or []
            ok(
                "vocab_practice_quiz",
                qstatus == 200 and (len(qs) >= 1 or isinstance(qdata, dict)),
                f"status={qstatus} type={type(qdata).__name__} qs={len(qs) if isinstance(qs, list) else '-'}",
            )
        except Exception as e:
            ok("vocab_block", False, str(e)[:250])
            traceback.print_exc()

        try:
            thpt = ThptMockService()
            out, st = thpt.generate_paper("smoke-teacher", SAMPLE, "A12", "gemini")
            if st >= 400:
                ok("thpt_generate", False, str(out)[:280])
            else:
                paper = out.get("paper") or out
                qs = paper.get("questions") or []
                ok(
                    "thpt_generate",
                    st in (200, 201) and len(qs) >= 5,
                    f"status={st} q={len(qs)} code={paper.get('share_code')} title={str(paper.get('title', ''))[:50]}",
                )
                if paper.get("share_code"):
                    pub, pst = thpt.get_by_share_code(paper["share_code"], include_answers=False)
                    ok("thpt_public", pst == 200 and bool((pub or {}).get("share_code") or (pub or {}).get("questions")), f"status={pst}")
        except Exception as e:
            ok("thpt_generate", False, str(e)[:280])
            traceback.print_exc()

        try:
            tts = TtsService()
            d, s = tts.generate(
                "smoke-teacher",
                "Hello students. Welcome to Bright Future English.",
                "en-US",
                False,
            )
            item = d.get("item") or {}
            ok("tts_generate", s == 201 and bool(item.get("audio_url")), f"status={s}")
        except Exception as e:
            ok("tts_generate", False, str(e)[:200])

        ok("thpt_levels", "A12" in LEVELS and "B12" in LEVELS and "C12" in LEVELS)

    fails = [r for r in results if r[0] == "FAIL"]
    print("---", f"{len(results) - len(fails)}/{len(results)} passed")
    raise SystemExit(1 if fails else 0)


if __name__ == "__main__":
    main()
