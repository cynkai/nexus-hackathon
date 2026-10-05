# Changelog

버전은 [SemVer](https://semver.org/lang/ko/)를 따른다 — 기능 추가는 가운데 자리(1.1.0), 버그 수정만 있으면 끝자리(1.1.1).

## [Unreleased]

## [1.0.0] — 2026-10-05

해커톤 제출본을 공개 레포로 정리한 첫 버전.

### Changed
- 서버 기본 바인딩 `0.0.0.0` → `127.0.0.1` (`NEXUS_HOST`로 바꿀 수 있다). LLM 키를 넣고 띄우면 같은 네트워크의 누구나 그 키로 호출할 수 있었다. `PORT`도 환경변수로.
- 대시보드 ETag가 고정값(`nexus-dashboard-v1`)이라 업데이트 후에도 1시간 동안 옛 화면이 보일 수 있었다 → 버전별 ETag.
- LICENSE·README 작성자 표기 "NEXUS Team" → `cynkai`.

### Added
- `VERSION` 파일, 대시보드 하단 버전 표시, CHANGELOG.
- CI: Python 3.10·3.13에서 스모크 테스트 (키 없이, 템플릿 경로).
- README: 한국어 요약, 환경변수 표, 알려진 한계.

### Known issues
- `NEXUS_LLM_API_KEY`를 넣으면 승객 안내 문장이 판단과 어긋날 수 있다 (가능한 환승을 "불가능"이라 하거나, 촉박함·고객센터 안내를 빠뜨림). 키를 넣은 스모크 테스트는 12건 실패. 기본(템플릿) 경로는 157/157.

## 0.x — 해커톤

- 2026-07-29 — 시나리오 현실성 개선, 추천 카드 한국어화 (`hackathon-submission` 태그, 제출 당시 최종 커밋).
- 2026-07-23 — MVP: 규칙 엔진, 3개 시나리오, 대시보드, 스모크 테스트.

[Unreleased]: https://github.com/cynkai/nexus-hackathon/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/cynkai/nexus-hackathon/releases/tag/v1.0.0
