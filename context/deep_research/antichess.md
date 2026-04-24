Chess Engines for a 24-Hour Hackathon: Standard Chess, Antichess, and What to Actually Fork
This is a practical, hackathon-oriented map of the chess-engine landscape as of April 2026. It covers the dominant engines for standard chess and antichess, the key design choices that define them, and a concrete recommendation for what to fork and what's realistic to ship in 24 hours.
TL;DR Recommendation for a 24-Hour Hackathon
Fork Fairy-Stockfish if you want one engine that can play both standard chess and antichess out of the box. Fairy-Stockfish is a Stockfish derivative that natively supports Antichess, Giveaway, Suicide, and Losers variants, plus everything on Lichess (Atomic, Crazyhouse, King of the Hill, Racing Kings, 3-Check), all under GPLv3 (Fairy-Stockfish GitHub).
Fork plain Stockfish 17.1 if you only care about standard chess — it's the world's strongest engine (~3759 Elo), open-source, and extremely well documented (Stockfish blog, Attacking Chess top-10).
Deploy on Lichess via the official lichess-bot bridge, which is a ~1-hour setup: point it at any UCI-compliant binary and you have a bot account playing rated games online (lichess-bot GitHub).
Realistic 24-hour deliverables: a tweaked evaluation or search parameter, a custom "personality," a UI wrapper, a deployed Lichess bot, a themed opening book, or — the coolest demo — swapping in an evaluation tweak that makes the engine play antichess more aggressively or more positionally. Training a strong NNUE from scratch is not realistic in 24 hours; fine-tuning an existing one is borderline.


Part 1 — Top Standard Chess Engines (2025–2026)
Stockfish (the unambiguous #1)
Stockfish 17.1 was released March 30, 2025, and at the time of the TCEC Season 28 Superfinal in September 2025 it won its 18th TCEC title, defeating Leela Chess Zero 57.5–42.5 — an unprecedented 11-in-a-row streak (Chessdom, Sept 2025). Stockfish 17.1 added roughly 20 Elo over Stockfish 17, and Stockfish 17 itself was ~46 Elo stronger than Stockfish 16 (Stockfish releases).

Search: Alpha-beta with principal variation search, late move reductions, null-move pruning, singular extensions, lazy SMP for multithreading.
Evaluation: NNUE (Efficiently Updatable Neural Network) — a small neural net (few MB) that is incrementally updated as moves are made. It runs on CPU, not GPU, which is why Stockfish is practical on any laptop.
Board representation: Bitboards (64-bit integers, one per piece type/color), with magic bitboards for sliding piece attacks.
License: GPLv3 (Stockfish GitHub).
Why it matters for a hackathon: It's the best-documented, most hackable strong engine in existence. The codebase is in C++, has an active Discord, and there's even a PyTorch NNUE trainer (nnue-pytorch) if you want to retrain the net (nnue-pytorch).
Leela Chess Zero (Lc0)
Leela is the strongest neural-network-MCTS engine and Stockfish's only real rival at the top. At TCEC Swiss 8 in May 2025 it was rated ~3693 Elo, and at the Season 28 Superfinal it was runner-up (Chessdom S28, Chessdom S28 final). It has played over 2.5 billion self-play training games as of June 2025 (Wikipedia – Leela Chess Zero).

Search: PUCT-based Monte Carlo Tree Search (MCTS) — fundamentally different from alpha-beta. Nodes are expanded proportional to a neural net's policy head, and values come from the net's value head (lczero.org dev overview).
Evaluation: Deep neural network (transformer-based since 2022, previously residual-CNN). Much larger than NNUE, designed to run on GPU, though CPU backends exist (Wikipedia – Leela).
Board representation: Bitboard-based input, tokenized as 64 board squares for the transformer (Wikipedia – Leela).
License: GPLv3 (lc0 GitHub).
Why it matters for a hackathon: Unless you have a fast GPU and existing ML experience, Lc0 is a harder fork target than Stockfish. Training new weights takes days to weeks. But if you want to demo a neural-net chess engine on GPU, Lc0 is the project.
Komodo Dragon
Dragon 3.3 (October 2023) is the final commercial release from the Komodo team after Mark Lefler and Larry Kaufman retired and Chess.com took over the project (Komodo blog, Chessprogramming wiki – Dragon). It uses NNUE plus alpha-beta, with an optional MCTS mode. It sits around 3615 Elo and is no longer actively updated — the Komodo team has largely migrated to the new Torch project (Chessdom S28).

Note for the hackathon: Dragon is commercial ($74.98 for 3.3), so it's not fork-friendly. Skip it as a base.
Torch (Chess.com's new engine)
Announced by Chess.com in 2023, Torch was built by a supergroup — Andrew Grant (Ethereal), Finn Eggers & Kim Kåhre (Koivisto), Jay Honnold (Berserk), and the Dragon team — and debuted as the world's #2 engine behind Stockfish (Chess.com – Torch announcement, Chessprogramming wiki – Torch). It joined TCEC Season 29 in late 2025 (Chessdom S28 article). Torch is not publicly available as source, so it's not usable as a hackathon base.
Other Notable Open-Source Engines (All Fork-Friendly Under GPLv3)
According to TCEC Season 28 ratings and recent CCRL lists, the strong open-source engines clustered just below Stockfish/Lc0 in late 2025 were roughly (Attacking Chess top-10, Chessdom S28):

Engine
Language
Elo (approx.)
License
Notes
Obsidian
C++
~3686
GPLv3
Rapidly rose to #3; NNUE + alpha-beta. Started April 2023 (Obsidian GitHub).
Berserk
C
~3646
GPLv3
By Jay Honnold; clean, readable code often recommended as a learning reference (Berserk GitHub).
PlentyChess
C++
~3647
open
NNUE with "threat-input" architecture (PlentyChess GitHub).
Caissa
C++
~3641
MIT
Custom NNUE, Chess960 support; friendly codebase started in 2021 (Caissa GitHub).
Integral
—
~3651
open
Led TCEC Swiss briefly (Attacking Chess top-10).
Ethereal
C
—
GPLv3 (non-NNUE free, NNUE commercial $60)
Classic, very readable. Free version is hand-crafted-eval; NNUE version is paid (Ethereal GitHub).
Viridithas
Rust
3400+
GPLv3
Strongest Rust engine; NNUE + alpha-beta (Viridithas GitHub).
Alexandria
C
—
GPLv3
Well-maintained NNUE engine, good for learners (Alexandria GitHub).
RubiChess, Koivisto, Stormphrax
various
~3500–3600
open
All reasonable starting points.


For a hackathon where you want a strong baseline with readable code, Berserk (C), Alexandria (C), Viridithas (Rust), or Caissa (C++, MIT license — the most permissive) are excellent forks that are much easier to understand than Stockfish's highly optimized codebase.
Recent Tournament Context
TCEC Season 28 (runs through Sept 2025): Stockfish won the Superfinal 57.5–42.5 over Lc0 — Stockfish's 18th TCEC title and 11th in a row (Chessdom).
TCEC Swiss 8 (May 2025): 44 engines, first-ever 3700+ engine in the field (Chessdom Swiss 8).
Chess.com CCC: 24/7 running tournament; Stockfish has won essentially all recent rapid/blitz/bullet titles, with occasional upsets by Lc0 at fast time controls (Chess.com CCC).


Part 2 — Antichess / Losing Chess / Suicide Chess
The Key Difference from Standard Chess
Antichess flips almost every assumption that standard chess engines bake in:

Captures are compulsory — if you can capture, you must. This completely changes move generation and makes long forced sequences extremely common, so search needs to go to a much higher depth to evaluate lines correctly (Lichess forum).
Losing all your pieces or being stalemated wins the game — so material evaluation is inverted: pieces are liabilities, not assets.
The king is not royal — it's just a mann piece, and pawns can promote to king. There's no check, no checkmate (in the standard sense), and no castling (Wikipedia – Losing chess).

Because of these rules, antichess engines tend to combine alpha-beta with proof-number search for finding long forced wins, and rely heavily on endgame tablebases — even more than standard chess engines do.
Antichess Is Weakly Solved
In October 2016, Mark Watkins (University of Sydney) announced that antichess is weakly solved: 1. e3 is a forced win for White under both FICS and International stalemate rules (Watkins paper PDF, Chessprogramming wiki – Losing Chess). The proof took about 5 years of computation on multiple 16-core servers using proof-number search plus endgame tablebases, and the full compressed solution tree is ~1 GB (~4.2 GB expanded) (Lichess blog – tolius). In 2025, an extension by the tolius project proved 1. e3 wins in fewer than 80 moves under the 50-move rule (Lichess – tolius blog).

Practical implication for the hackathon: any serious antichess engine should know about (or even incorporate) the Watkins 1.e3 lines for the White opening book, and should use the Lichess antichess tablebases for endgames.
Top Current Antichess Engines
Fairy-Stockfish is the dominant general-purpose antichess engine today. It's the engine Lichess uses for server-side analysis of every Lichess variant (including antichess, atomic, 3-Check, King of the Hill, Racing Kings, and Crazyhouse) (Fairy-Stockfish online). It supports Antichess, Giveaway, Suicide, Losers, and Codrus as separate rule variants, and has a specifically trained NNUE for antichess that adds >100 Elo over the hand-crafted evaluation (Fairy-Stockfish releases, Fairy-Stockfish NNUE wiki).

Anti-Fairy (by SriMethan) is a dedicated fork of Fairy-Stockfish focused specifically on antichess variants, built for the liantichess community — it's a useful reference if you want antichess-only optimizations (Anti-Fairy GitHub).

Nilatac (Cătălin Francu) is the classic antichess engine — originally built for FICS in the early 2000s, it still runs on Lichess under the account @Nilatac (and its weaker sibling @CatNail). It's no longer actively developed but its opening book (browseable at catalin.francu.com) is a gold mine for anyone wanting forced-win lines, and it uses proof-number search specifically tuned for antichess (Nilatac site, Nilatac opening book).

Nakshatra (by goutham) is another open-source antichess-capable engine, originally FICS-focused, with support for both standard and antichess (Nakshatra GitHub).

Sjeng (Gian-Carlo Pascutto) is historical but still relevant context: the open-source Sjeng 11.2 (2002) was one of the first strong engines to support suicide/losers variants, using alpha-beta plus proof-number search; Sjeng went closed-source after, becoming Deep Sjeng (Chessprogramming wiki – Sjeng, Sjeng GitHub). Sunsetter (George von Zimmermann) is similarly historical — it's a Crazyhouse/Bughouse engine, not directly antichess, sometimes confused with it (Chessprogramming wiki – Sunsetter).
Top Antichess Bots on Lichess (Late 2025 / Early 2026)
Based on Lichess community bot leaderboards and game history, the notable antichess bots include:

IAFantichessBot — the International Antichess Federation's official bot (~2613 rating) (lichess.org/@/IAFantichessBot).
anti-bot — a popular "play-like-a-human" antichess bot with 9 levels, 100k+ games played (lichess.org/@/anti-bot).
Fairy-Stockfish (official bot account, operated by the author @ubdip) — plays all variants at ~2464 Elo on Lichess's rating scale (lichess.org/@/Fairy-Stockfish).
Nilatac / CatNail — Francu's bots, still online (Nilatac site).
LeelaMultiPoss tops the overall bullet/blitz bot leaderboards on Lichess (#1 bullet at 3322, #1 blitz at 3234 as of Oct 2025), but this is a standard-chess bot, not antichess (Top Bots Leaderboard).
Antichess Endgame Tablebases
Lichess hosts antichess tablebases up to 4 pieces via their public API at tablebase.lichess.ovh/antichess — this is significantly smaller than the standard-chess 7-piece Syzygy tables but still very useful for engine endgame play (Lichess API – tablebase, lila-tablebase GitHub). The tablebase returns DTW (Depth To Win) metrics specific to antichess. No 7-piece antichess tablebases exist because they're computationally harder than standard and interest is smaller (Lichess forum).


Part 3 — Implementation Concepts at a Glance
All modern top engines share a core architecture, with two major divergent families:



Alpha-beta family (Stockfish, Obsidian, Berserk, Fairy-Stockfish, most of the top-15)
MCTS family (Lc0, Komodo Dragon's MCTS mode, Stoofvlees)
Search
Alpha-beta with PVS, null-move pruning, late move reductions, singular extensions, killer/history heuristics, lazy SMP threading
PUCT-based Monte Carlo Tree Search; leaf evaluations from the neural net's value head, move priors from the policy head
Evaluation
NNUE — small (~few MB), CPU-friendly, incrementally updated; or classical hand-crafted (pieces + PSQT + pawn structure + king safety, tuned with Texel tuning)
Deep neural network (tens to hundreds of MB); runs best on GPU; outputs both a policy distribution and a value
Strength per node
High NPS (~millions/sec), shallower per-position evaluation
Lower NPS (~10–100k/sec on GPU), much deeper per-position understanding
Hackathon fit
Much better. Runs on a laptop CPU, iterates in seconds, no GPU needed.
Requires GPU and ML know-how; training is slow.


Board representation is nearly universal at the top level: bitboards — 64-bit integers where each bit represents a square, with one bitboard per (color, piece-type) plus magic bitboards for sliding piece moves. This is extremely fast on 64-bit CPUs and is what you'll find in Stockfish, Berserk, Caissa, Viridithas, Alexandria, and essentially every modern engine (BBC tutorial, dev.to deep dive).

Why it matters for hackathon teams: Do not try to write a bitboard move generator from scratch in 24 hours unless one teammate has done it before. Fork an existing engine and modify higher-level pieces — evaluation weights, search parameters, move ordering, a personality, UI, or deployment.


Part 4 — The Hackathon Playbook
Best Base to Fork
Fairy-Stockfish (GPLv3) — the best choice if you want both standard chess and antichess. Compile once, pass -DUCI_Variant antichess (or the variant's UCI option) and you have an engine that plays both at very high level (Fairy-Stockfish GitHub). Variant NNUE files are available as separate downloads (Fairy-Stockfish NNUE).
Stockfish 17.1 (GPLv3) — if only standard chess matters. World's strongest, best documentation, largest community (Stockfish).
Berserk, Alexandria, Caissa, Viridithas — for teams who want a readable codebase to actually understand and modify. Berserk (C) and Alexandria (C) are especially well-regarded as teaching references. Caissa is under MIT license, unlike the GPLv3 engines, which matters if you're worried about downstream licensing.
What You Can Realistically Ship in 24 Hours
✅ Tweak evaluation weights / search parameters (~2–6 hours). Edit piece values, PSQT tables, king-safety weights, LMR/null-move depths, or contempt settings. Measurable Elo change within a few minutes of self-play testing. This is the bread and butter.
✅ Build a UCI-compatible Lichess bot (~1–2 hours). Use lichess-bot from lichess-bot-devs: it's a Python bridge that connects any UCI engine to the Lichess Bot API. You register a fresh Lichess account, upgrade it to BOT via POST /api/bot/account/upgrade with a token, set your engine binary path in config.yml, and run it (lichess-bot GitHub, Lichess bot upgrade guide). The bot can play both standard chess and antichess if the engine supports it, which Fairy-Stockfish does.
✅ Integrate with a web UI (~3–6 hours). python-chess + any JS board (chessground, chessboard.js) on a Flask/FastAPI backend communicating with the engine via UCI. The Lichess Chessground is their own open-source board library and is production-grade.
✅ Build a themed/personality engine (~4–8 hours). Stockfish has a "Skill Level" and contempt setting; Komodo Dragon introduced "Personalities" (Active, Positional, Defensive, Human, Beginner etc.) — you can mimic this by scaling eval terms. A "gambit-loving" or "king-hunter" variant is a crowd-pleasing demo.
✅ Antichess-specific hacks: prepending the Watkins 1.e3 opening lines into your engine's book for guaranteed wins as White (legally gray on Lichess — see below), tuning evaluation so that your engine values tempo and avoids captures that free the opponent.
⚠️ Fine-tuning an existing NNUE (~6–12 hours). Possible with nnue-pytorch if you have training data and a GPU, but risky to debug inside 24 hours (nnue-pytorch).
❌ Training an NNUE from scratch (days to weeks). Not realistic. Stockfish uses billions of positions and hundreds of CPU/GPU-hours.
❌ Writing a competitive engine from scratch. Even the simplest-to-read tutorials (e.g., Maksim Korzh's 95-video "BBC" series) take weeks to implement fully (BBC chess engine). A toy engine is fine as a learning exercise, but it will be ~1500 Elo, not competitive.
Deployment: Lichess Bot API
The official path is:

Create a new Lichess account (no games played yet).
Generate an API token at lichess.org/account/oauth/token/create with bot scopes.
Run curl -d '' https://lichess.org/api/bot/account/upgrade -H "Authorization: Bearer YOUR_TOKEN" to convert the account to a BOT account (irreversible) (Lichess forum guide).
Clone lichess-bot-devs/lichess-bot, put your engine binary in engines/, edit config.yml to point at it, and run python lichess-bot.py (lichess-bot GitHub).
lichess-bot automatically handles both standard chess and variants — just list them in the challenge.variants list in config.yml.

The config.yml also supports opening books (Polyglot format), online endgame tablebase lookups (including Lichess's own antichess tablebase for 3–4 pieces), and a "homemade" engine mode where you write the engine logic directly in Python inside the bot loop — useful if your team's "engine" is actually a Python ML model (lichess-bot config docs).
Licensing Considerations
Everything strong and open in this report except Caissa is GPLv3. That means if you fork Stockfish, Fairy-Stockfish, Lc0, Berserk, Ethereal, Viridithas, or Alexandria and distribute the result, you must release your source under GPLv3 too (Stockfish GitHub – license). For a hackathon demo this is usually fine — you're demoing code, not selling it — but if you want a permissive fork for later commercialization, Caissa's MIT license makes it the cleanest base (Caissa GitHub).
One Word of Warning About the Watkins Solution
Using Watkins's published solution files to play perfect antichess as White is a known gray area on Lichess. The solution is public and legitimate scholarship, but a bot that plays 100% "perfect book-Watkins" games could be viewed as uninteresting or flagged as a memorized-solution gimmick (Lichess forum discussion). For a hackathon demo, integrating Watkins lines as an opening book is fair game and genuinely impressive; marketing your bot as "unbeatable as White" is accurate but unoriginal.


Final Recommendation Summary
Goal
Fork
Time
Demo
Both chess & antichess bot on Lichess
Fairy-Stockfish
4–8h
Deployed Lichess bot playing both variants
Strongest possible standard-chess bot
Stockfish 17.1
2–4h
Personality/eval tweak + Lichess deployment
Learn-by-doing engine mod
Berserk / Alexandria / Caissa
8–16h
Custom eval or search heuristic with measured Elo delta
Antichess-specialized bot
Fairy-Stockfish + Watkins book
6–10h
Bot deployed with 1.e3 solution integrated
Neural-net demo on GPU
Lc0
12–20h
Small custom net or visualization of MCTS tree


For the best combination of "looks impressive," "actually works in 24 hours," and "handles both variants": fork Fairy-Stockfish, add a custom evaluation personality or an antichess opening book, wrap it with lichess-bot, and deploy it live to the Lichess bot arena. You'll have a bot playing rated games on the internet by the end of day 1 — which is a much more compelling hackathon demo than any amount of algorithm tweaking on a local machine.

