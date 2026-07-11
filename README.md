# 📈 stock-briefing

국내·미국 주식의 뉴스/공시/시세를 매일 자동 수집해 **요약 브리핑 메일**을 발송하고,
쌓인 데이터 위에서 **RAG Q&A · 도구 호출 에이전트 · MCP 서버**를 제공하는 개인 프로젝트입니다.

> 매일 아침 7시 15분(KST), GitHub Actions가 수집 → 인덱싱 → 브리핑 발송을 자동 실행합니다.
> 전 기간 **무료 티어만으로 운영** (LLM API 유료 환산 비용 기준 총 22원 상당, 실지출 $0).

<!-- 스크린샷: docs/images/briefing.png (이메일 브리핑), app.png (Streamlit), mcp.png (Claude Desktop 연동) -->

## 주요 기능

**1. 데일리 브리핑 (자동)** — 뉴스 클러스터링으로 "오늘의 이슈 Top 5"를 뽑아 LLM 요약,
관련 종목 매핑, 전일 시세, 간밤 미국 시장, 관심종목 공시를 HTML 메일로 발송

**2. RAG Q&A** — "어제 삼성전자 관련 무슨 일 있었어?" → 수집 기사에서 검색해
출처 번호를 인용하며 답변. 한국어 질문으로 영문 기사 검색(교차 언어) 지원

**3. 도구 호출 에이전트** — LLM이 `get_price` / `search_news` / `get_disclosures`
도구를 스스로 선택 호출. "SK하이닉스 주가랑 ADR 상장 소식 같이 알려줘" 같은 복합 질문 처리

**4. MCP 서버** — 위 도구들을 Model Context Protocol 표준으로 노출,
Claude Desktop 등 MCP 클라이언트가 이 프로젝트의 데이터를 직접 조회 가능

**5. Streamlit 데모** — 에이전트 채팅 + 수집/사용량 대시보드 (`streamlit run app.py`)

## 아키텍처

```
[수집: 매일 07:15 KST, GitHub Actions]
  뉴스 RSS (한국경제·MarketWatch·Yahoo) ─┐
  공시 (DART OpenAPI · SEC EDGAR)       ├→ SQLite (market 필드, UTC, 중복 제거)
  시세 (yfinance: KR·US·지수·환율)      ─┘        │
                                                  ├→ [인덱싱] 제목 임베딩 저장
                                                  │     (gemini-embedding-001)
[브리핑] 클러스터링 → 이슈 Top5 → 요약 → HTML 메일 ┘
[Q&A]   질문 임베딩 → 코사인 top-k → 출처 인용 답변
[에이전트/MCP] 도구 3종 (시세·뉴스·공시)
```

## 기술 스택

| 영역 | 선택 | 비고 |
|---|---|---|
| LLM / 임베딩 | Gemini API 무료 티어 (flash-lite / embedding-001) | 호출부 추상화로 provider 교체 가능 |
| 데이터 | 한국경제 RSS, MarketWatch, Yahoo Finance, DART, SEC EDGAR, yfinance | 전부 무료 소스 |
| 저장 | SQLite + numpy 브루트포스 벡터 검색 | 수천 건 규모에선 벡터DB보다 단순·충분 (규모 확장 시 교체 지점 명시) |
| 자동화 | GitHub Actions (수집→인덱싱→발송→DB 커밋) | 실패 시에도 수집분 보존 (`if: always()`) |
| 발송 | Gmail SMTP, HTML 템플릿 | |
| 인터페이스 | CLI 챗 / Streamlit / MCP 서버 (FastMCP) | |

## 핵심 설계 원칙

1. **수치는 LLM이 만들지 않는다** — 주가·공시·날짜는 DB에서 직접 삽입하거나 도구 호출로만 획득.
   LLM은 서술만 담당. 에이전트에는 학습 기억 속 시세 사용을 명시적으로 금지
2. **부분 실패는 축소 동작으로** — 피드 하나가 죽어도 나머지 수집, 이슈 추출이 실패해도
   시세·공시만으로 브리핑 발송
3. **모든 LLM 호출 로깅** — 토큰·지연시간·용도를 DB에 기록, 사용량/환산 비용 리포트 제공
4. **평가 없이는 개선 없음** — 골든셋 기반 정량 평가로만 변경을 채택 (아래)

## 평가

### 검색 (골든셋: 직접 라벨링한 질문 30개)

| method | recall@3 | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| **vector (채택)** | **0.515** | **0.743** | **0.903** | **0.799** |
| bm25 | 0.173 | 0.265 | 0.358 | 0.446 |
| hybrid (RRF) | 0.286 | 0.490 | 0.714 | 0.593 |

하이브리드 검색은 **부정적 결과**: 대화체 한국어 질문 + 제목 코퍼스 조합에서 BM25 신호가
약해, 동등 가중 융합이 오히려 벡터 검색을 오염시킴을 확인하고 벡터 단독을 채택.

### 생성 (LLM-as-judge + 수동 교차 검증)

- 충실성 5.0/5, 환각 0%, no-answer 질문의 올바른 "모름" 응답 14/14
- 수동 검증에서 심판이 놓친 미묘한 과잉 인과 연결 1건 발견 → 심판 점수는 상한선으로 해석,
  한계(자기 채점 편향, 제목 코퍼스의 낮은 난도)를 기록

### 가드레일 (공격 15종 + 과잉 방어 체크 3종, 4회 반복 측정)

- 최종 **공격 방어 100% (15/15), 과잉 방어 0 (정상 질문 3/3)**
- 반복 측정으로 발견·수정한 것: 창작 프레이밍 우회(소설 대사로 종목 추천 유도),
  에이전트의 학습 기억 기반 구식 시세 환각, 심판의 시간 맥락 부재로 인한 오판

상세한 실험·장애 대응 기록은 [EXPERIMENTS.md](EXPERIMENTS.md) 참고
(임베딩 한도 초과 장애 분석, 임베딩 재사용으로 호출 절반 감축, KRX 로그인 의무화 대응 등).

## 실행 방법

```bash
git clone https://github.com/namjunseo/stock-briefing.git
cd stock-briefing
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cat > .env << 'ENV'
DART_API_KEY=...        # opendart.fss.or.kr
GEMINI_API_KEY=...      # aistudio.google.com (무료)
GMAIL_ADDRESS=...
GMAIL_APP_PASSWORD=...  # 브리핑 발송용 (선택)
ENV

python collect.py                  # 수집
python index.py                    # RAG 인덱싱
python send_briefing.py --dry-run  # 브리핑 미리보기 (briefing.html)
python chat.py                     # RAG Q&A
python agent_chat.py               # 도구 호출 에이전트
streamlit run app.py               # 웹 데모
python -m eval.run_eval            # 검색 평가 재현
```

MCP 서버는 `mcp_server.py`를 MCP 클라이언트(Claude Desktop 등)에 등록해 사용.

## 한계와 다음 단계

- **제목만 수집** — 본문 미수집으로 검색·요약의 정보량에 상한. 본문 도입 시 청킹 전략과
  평가 재설계 필요 (가장 큰 다음 단계)
- **관심종목 범위** — KR 7 / US 17 종목 수동 관리. 종목 리스트 자동화는 KRX 로그인
  의무화(2025.12) 이후 보류
- **심판 편향** — 생성 평가의 심판이 생성 모델과 동일. 이종 모델 심판 도입 예정
- **시간 표현 질의** — "어제" 등의 자동 날짜 필터링 미구현 (수동 `--days` 옵션만)

## License

MIT
