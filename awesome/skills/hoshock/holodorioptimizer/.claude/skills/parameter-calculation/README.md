# parameter-calculation

Source repository: [Hoshock/HolodoriOptimizer](https://github.com/Hoshock/HolodoriOptimizer)

Canonical key: `hoshock/holodorioptimizer:.claude/skills/parameter-calculation`

Manifest: [https://github.com/Hoshock/HolodoriOptimizer/blob/main/.claude/skills/parameter-calculation/SKILL.md](https://github.com/Hoshock/HolodoriOptimizer/blob/main/.claude/skills/parameter-calculation/SKILL.md)

## Description

What: ホロドリのユニット編成画面の「総合力」の構造（6 項目の加算・素値基準・切り上げ。2026-09-08 実機内訳で確定）と、カード詳細画面に表示される P/T/S がどう計算されるか（レベル・開花・青/緑ホロメンボード・所属ボーナスの反映と、赤ボード・メモリー・強化ボーナス・スキルの不反映）と、ユニットスコア計算で別枠として扱う要素の定義。青ホロメンボードの全ホロメン共通ノード構成（31 マスの座標・効果・左右型）、緑ホロメンボードの全ホロメン共通ノード構成（24 マスの座標・効果・所属別の値）、黄ホロメンボードの全ホロメン共通ノード構成（31 マスの座標・楽曲スコアボーナスとホロワーク報酬の効果・左右型。アカウント全体に効き上限 10.0%、曲選択時はスコアボーナスのホロメンボード効果欄に入る — 2026-09-11 実機確定）、赤ホロメンボードの全ホロメン共通ノード構成（63 マスを上 / ライフ系 / ステータス系の 3 エリアで。リーダー用でメンバー 5 人に効く。左右は lifeSide）、4 色ボードの全体配置（赤上・緑下・青黄左右、左右はホロメン別に固定）も持つ。実機観測で確定した「変わらない事実」だけを持つ。
Use when: スコア計算エンジン（src/engine/、src/data/bloom.ts）やカードデータ（src/data/cards.json の stats）を設計・変更するとき、実測したカード値とデータを照合するとき、ホロメンボード補正の入力方式を設計するとき、ユーザーが「パラメータ」「ボード」「開花の上昇量」「メモリー」「強化ボーナス」に触れたとき。


## Classification

Categories: architecture, data, design, documentation, testing
Client compatibility: Claude Code, GitHub Copilot
License: MIT

## Resources

Scripts: 0
References: 5
Assets: 0
Other: 0

## Scores

Overall: 96
Quality: 85
Security: 100
Maintenance: 100
Adoption: 10

## Static security findings

No static findings recorded

Static analysis is not malware certification

## Publication metadata

First seen: unknown
Indexed: 2026-09-11T16:46:46.333393+00:00
Published: 2026-09-11T19:23:00.429355+00:00
Publication event: add
Source fingerprint: `33f3bd1307ba6181760bdc9b0e9740940548bdec20c089d0bfca75886c573d8c`
Analysis fingerprint: `9aa6fc14975b3064caa10c7fc04c4f909da23002f83a5d3738c68baa7ce164c0`
