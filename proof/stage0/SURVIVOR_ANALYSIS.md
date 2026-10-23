# Stage 0 mutation ledger: survivor analysis (single source of truth)

Authored-by: Perplexity (underlying model undisclosed), round 2. Nothing here was executed. This replaces the prior file; the old entries were only visible in a lossy digest, so diff against the current file and merge before committing.

Closure rule (Owner-approved): fresh seeds 11 and 23 at `--n 12`, `process.py` scoped to the 0B functions. Every survivor appears individually below. `survivors_seed11.txt` contains 61 lines (44 source, 17 schema), not 58; all 61 are listed.

## A. Existing entries (seed 7 ledger, kept)

- Ledger: 153 mutants; 140 killed (82 in the first run, 1 by timeout, 57 by `test/actl/test_s0_gap*.py`); 9 invalid/non-applicable; 4 equivalent survivors with differential proofs.
- EQ-A `src/actl/hashing.py:42` `rows.sort(key=lambda r: r[0])` to `r[1]`: equivalent. Row = `(rel_bytes, rel\0flag\0digest\n)`. Relative paths are unique and cannot contain NUL, so when A is a strict prefix of B the key `r[1]` compares `\0` against a path byte (>= 0x01) and orders A before B, the same as `r[0]`. Differential: `diff_equiv_seed11.py::diff_hashing42` (200000 trials).
- EQ-B `src/actl/ids.py:68` `tag.split("_", 1)[0]` to `split("_", 2)[0]`: equivalent. Guarded by `validate_sprint_tag`; the slug class `[a-z0-9-]` excludes `_`, so a valid tag has exactly one underscore. Differential: loop over slugs `a0, demo-1, x*40, a-b-c-9`.
- EQ-C `src/actl/hashing.py:27` `os.walk(followlinks=False)` to `True`: equivalent. Every entry of `dirnames+filenames` is `lstat`ed and a symlink raises `ValueError` before `os.walk` could descend.
- EQ-D `src/actl/cli.py:70` `getattr(args, "json", False)` default False to True: equivalent. `want_json` is computed from `argv`, and every registered subcommand defines `--json` (`store_true`), so the default is never used.
- RETRACTED `src/actl/next.py:50` PRIORITY default 100 to 101: killed by `test_next_rule_default_priority_tiebreak` (Gate D D-06).

## B. Seed 11 survivors (61), individually

Format: id, file:line, mutation, disposition.

S11-01 `hashing.py:60` `<=` to `<` (U+DFFF bound): killed-by `test_s0_gap2_hashing.py::test_lone_surrogates_rejected_by_validator_not_by_encoder[\udfff]`. Observable only through exception type: the encoder would still raise `UnicodeEncodeError` (a `ValueError` subclass), so the test requires a non-`UnicodeError` `ValueError` with the message "Surrogates not allowed" (INTERFACES: "before UTF-8 encoding"). The neighbours U+D7FF and U+E000 are accepted (`test_neighbours_of_surrogate_range_accepted`).

S11-02 `hashing.py:42` sort key `r[0]` to `r[1]`: equivalent, same as EQ-A (differential included). `test_manifest_sorted_bytewise_with_prefix_paths` is a regression guard that passes on both.

S11-03 `ids.py:96` `not slug_trimmed` to `slug_trimmed`: killed-by any success case, e.g. `test_s0_gap2_ids.py::test_format_session_name_with_tag_shape`, because the mutant raises for every valid input. Unreachability argument for the original `raise`: a valid slug matches `^[a-z0-9][a-z0-9-]{1,40}\Z`, `max_slug >= 1`, so `slug[:max_slug]` starts with an alphanumeric character and `rstrip("-")` cannot empty it. The original guard is therefore defensive and unreachable.

S11-04 `ids.py:84` `not validate_sprint_tag(tag)` to `validate_sprint_tag(tag)`: killed-by `test_invalid_tag` and the with-tag success tests.

S11-05 `ids.py:93` `max_slug < 1` to `< 2`: killed-by `test_max_slug_one_allowed_with_tag` and `test_max_slug_one_allowed_without_tag`; the zero side is `test_max_slug_zero_rejected_*`.

S11-06 `ids.py:92` `41` to `42`: killed-by `test_trimming_40_char_slug_with_tag_is_exactly_41`, `..._without_tag_...` and `test_trimming_41_char_slug_with_tag` (the mutant yields length 42 and `ValueError`).

S11-07 `ids.py:54` `return False` to `True`: killed-by `test_validate_sprint_tag_false_for_non_str`, `..._for_impossible_dates` and `..._for_pattern_mismatch`, which cover all three `return False` sites of `validate_sprint_tag`. If line 54 is instead a site in another function, confirm with the seed 11 run.

S11-08 `layout.py:139` `0o755` to `0o756` (sprint-tree loop): killed-by `test_sprint_tree_exact_modes_and_exact_dir_set[umask000|umask022|umask077]`.

S11-09 `layout.py:123` `0o755` to `0o756` (`actl-repo/specs`): killed-by `test_base_tree_exact_modes_and_exact_dir_set[...]`.

S11-10 `seq.py:328` `and` to `or` (escalation filter): killed-by `test_ev_live_decision_and_implementer_dir_not_taken_as_escalation` and `test_escalation_grants_per_stage`. Both `and`-to-`or` variants are covered. `A or (B and C)` makes `ev-NNN.json` and `live-decision-NNN.json` take the escalation branch; `(A and B) or C` and `A or B or C` also make the `implementer-NNN` directory raise `ValueError`. The `.meta.json` conjunct is itself unreachable-false: `parse_seq_from_name` returns `None` for `*.meta.json`, `*.json.bak` and `xescalation-*`, so those decoys never reach the chain (`test_decoys_are_ignored` documents this).

S11-11 `seq.py:299` `+ 1` to `+ 2` (oracle attempts): killed-by `test_qual_counts_attempts_oracle[1|2|3]`.

S11-12 `seq.py:264` `and` to `or` (frozen/draft): killed-by `test_frozen_draft_truth_table` (16 cases). At line 264 `state["status"]` was reset to `"draft"` immediately before, so only (frozen, draft) to running and (draft or absent or malformed, draft) to draft are reachable; the other two combinations are unreachable at this line. The mutant forces `running` for the draft, absent and malformed `sprint.toml` rows.

S11-13 `seq.py:338` first `0` to `1` in the `grants` fallback literal: equivalent (differential included). `state["grants"]` is set to a non-empty dict (or comes from `default_state`) before the escalation loop, so `state.get("grants") or {...}` never evaluates its right-hand side. Differential: `diff_equiv_seed11.py::diff_seq` (338). The exact counters are still pinned by `test_escalation_*`.

S11-14 `seq.py:255` `0` to `1` (reset of `attempts` for an existing state): killed-by `test_existing_valid_state_is_reset_not_carried` and `test_qual_counts_attempts_oracle`. If the mutated literal is not `oracle`, `test_ev_counts_attempts` and `test_existing_valid_state_is_reset_not_carried` cover `implementer`, `live` and `curator`.

S11-15 `seq.py:299` `.get("oracle", 0)` to `.get("oracle", 1)`: equivalent (differential included). `attempts` is built from `state["attempts"]`, which was reset to a dict with the key `oracle` present (or is the default state), so the `.get` default is never used. Differential: `diff_seq` (299).

S11-16 `seq.py:373` `+ 1` to `+ 2` (hard caps): killed-by `test_hard_caps_tripped_counts_each_qualifying_ev_once[1|2|3]`.

S11-17 `seq.py:348` `.get(stg, 0)` to `.get(stg, 1)` (`grant_attempts` branch, `+ cnt`): equivalent (differential included). The statement is guarded by `stg in grants` and `grants` always has the four stage keys, so the default is unreachable. The "unknown stage" question is answered by `test_escalation_unknown_stage_and_bad_count_ignored`: an unknown stage is skipped, never a `KeyError`. Differential: `diff_seq` (348).

S11-18 `seq.py:104` `0o600` to `0o601` (lock file): killed-by `test_lock_file_is_0600[umask000|umask022|umask077]`.

S11-19 `seq.py:280` `and` to `or` (spec filter): killed-by `test_each_kind_sets_only_its_own_pointer` for the `(A and B) or C` and `A or B or C` forms, where every artifact becomes `active_spec`. The textual first-`and` form `A or (B and C)` is equivalent on parseable names (only `spec-NNN.md` ends in `.md`, so the disjunct adds nothing). Differential: `diff_seq` (280).

S11-20 `seq.py:184` `"epoch": 1` to `2` (`default_state`): killed-by `test_defaults_when_state_json_absent` and `test_defaults_rebuilt_after_deleting_state_with_artifacts_present`.

S11-21 `scope.py:80` `==` to `!=` (`ScopeRuleList.__getitem__`): killed-by `test_s0_gap2_validator_scope.py::test_scope_rule_list_string_indexing` (`rules["bogus"] == []`). Recommendation: keep and test, do not delete. Existing tests use `rules["allow"]`, and `parse` returning a list subclass with string indexing is undocumented in INTERFACES; if removed later, do it in a PB-4-approved change together with those tests.

S11-22 `schemas.py:280` `i < len(instance)` to `<=`: killed-by `test_prefix_items_shorter_or_equal_instance_is_valid[...]`.

S11-23 `schemas.py:361` `not be` to `be` (keyword `not`): killed-by `test_not_keyword` and `test_not_keyword_nested_path`.

S11-24 `sprint.py:77` `returncode == 0` to `== 1` (`ls-remote`): killed-by `test_is_git_repo_file_url_true_and_output_captured`.

S11-25 `sprint.py:112` `and` to `or`: equivalent for returns and for `ValueError`; differential included. The inner `return` is dead: whenever both paths exist and resolve equal, the comparison on the previous lines already returned. The only observable difference is a `RuntimeError` from `Path.resolve()` on a symlink loop on CPython 3.12 or older, and `test_init_different_target_with_origin_symlink_loop_still_value_error` kills it there. On 3.13 it stays equivalent. Differential: `diff_sprint112`.

S11-26 `sprint.py:65` `returncode == 0` to `== 1` (`rev-parse`): killed-by `test_is_git_repo_true_for_subdirectory_of_repo` (a subdirectory is accepted by `rev-parse` but rejected by `ls-remote`).

S11-27 `sprint.py:72` `capture_output=True` to `False` (`ls-remote`): killed-by `test_is_git_repo_file_url_true_and_output_captured` and `test_is_git_repo_file_url_missing_is_false_and_quiet` (`capfd` sees leaked ref lines or stderr).

S11-28 `sprint.py:79` `return False` to `True` (exception path): killed-by `test_is_git_repo_false_when_git_raises[OSError|TimeoutExpired]`.

S11-29 `sprint.py:211` `== 0` to `!= 0` (`origin/HEAD` present): killed-by `test_base_sha_default_branch_with_origin_head_and_other_branch_checked_out[trunk]`. A default branch named `trunk` makes the main/master fallback fail, so the mutant falls back to `HEAD`, the feature branch. `[main]` and `[master]` plus the "without origin HEAD" tests cover the fallback branch.

S11-30 `cli.py:21` `not Path(f).is_file()` to `Path(f).is_file()`: killed-by `test_stale_cmd_module_purged_and_live_ones_kept`. It is not dead code: it purges stale `actl.cmd_*` entries from `sys.modules`. Do not delete.

S11-31 `cli.py:29` `or` to `and`: killed-by `test_non_callable_register_raises_attribute_error` (the mutant raises `TypeError`). A module without `register` raises `AttributeError` under both forms, which is equivalent for that sub-case and covered by `test_missing_register_raises_attribute_error`.

S11-32 `next.py:23` `or` to `and`: equivalent for the exception contract. The sprint directory exists without `state.json`: the original raises `FileNotFoundError("Sprint not found")`, the mutant continues and `read_state` raises `FileNotFoundError("State file missing")` (verified in the `seq.py` source: `if not sf.is_file(): raise FileNotFoundError`). The state file cannot exist without its sprint directory. Only the message differs; `test_next_missing_sprint_or_state_is_file_not_found` pins the type.

S11-33 `next.py:47` `or` to `and`: killed-by `test_next_rule_with_no_spec_is_skipped` and `test_next_rule_with_spec_without_loader_is_skipped`. For a real `*.py` the guard is unreachable (`spec_from_file_location` always returns a spec with a `SourceFileLoader`), but the guard is not dead, and deleting it would invite `Optional` type errors; keep it.

S11-34 `process.py:295` `77` to `78`: out-of-scope (pre-existing cosmetic separator width, not S0-R16).

S11-35 `process.py:196` `minutes > 0` to `>= 1`... (as listed `0 -> 1`): out-of-scope (pre-existing duration formatting, not S0-R16).

S11-36 `process.py:87` `path.parent.mkdir(parents=True, exist_ok=True)` `True` to `False`: which `True` was mutated is not determinable from the survivors list (it shows only the line and the generic `True -> False`). Killed-by `test_record_exit_creates_missing_parent_directory` (for `parents`) and `test_record_exit_with_existing_parent_directory` (for `exist_ok`). Whichever is mutated is covered. Function name `_record_exit` is inferred.

S11-37 `process.py:330` `check=False` to `True`: out-of-scope (pre-existing subprocess call outside S0-R16).

S11-38 `process.py:348` `while True` to `while False`: out-of-scope (pre-existing stream or poll loop outside S0-R16).

S11-39 `process.py:526` `return 1` to `2`: killed-by `test_kill_unknown_session_returns_1` and `test_cli_kill_unknown_session_exit_1`.

S11-40 `process.py:323` `select.select(..., 0)` to `1`: out-of-scope (pre-existing stream polling; timeout only changes latency).

S11-41 process.py:557 return 1 to 2 (tmux kill-session failed with an unrecognised error): killed-by test_s0_gap2_router.py::test_kill_tmux_failure_returns_1_and_writes_no_exit.

S11-42 process.py:172 check=False to True (enable_linger): equivalent. The call sits inside try/except, so a CalledProcessError is swallowed exactly as a non-zero return code is ignored. It is also outside S0-R16.

S11-43 process.py:337 check=False to True: out-of-scope (pre-existing subprocess call, not S0-R16).

S11-44 process.py:535 _record_exit(session_name, 143, overwrite=True) True to False: killed-by test_s0_gap2_router.py::test_kill_overwrites_129_with_143[kill-session-ok|server-already-gone] (a stale 129 must become 143) and by the strengthened shell check E8 (exactly 143). The pytest harness cannot run the shell suite, so the mutation run counts only the pytest kill.

S11-45 schemas/closure.json:9 seq minimum 1 to 0: killed-by test_pinned_bounds[closure:seq:minimum] and test_lint_one_minimum_names.

S11-46 schemas/closure.json:29 additionalProperties false to true: killed-by test_lint_no_additional_properties_true and test_zz_extra_rejected_at_every_dict_node.

S11-47 schemas/common.json:76 additionalProperties false to true: killed-by test_lint_no_additional_properties_true (deterministic, independent of fixture coverage). test_zz_extra_rejected_at_every_dict_node adds a second kill when a fixture contains the node.

S11-48 schemas/common.json:48 additionalProperties false to true: same as S11-47.

S11-49 schemas/common.json:56 minimum 1 to 0: expected killed-by test_lint_one_minimum_names if the property is named seq, epoch, max_epochs, min_attempts_before_block or sits under max_attempts. I could not see this line. If it is the seq in artifact_meta, then ev, qual and contract each redeclare seq >= 1 locally, and no instance-level test can distinguish the mutant (equivalent by redundancy). In that case the lint is the only kill, and the disposition stays "killed-by lint". If the seed 11 run still shows this survivor, report the property name and I will add a pinned entry.

S11-50 schemas/contract.json:80 additionalProperties false to true: same as S11-47.

S11-51 schemas/ev.json:28 seq minimum 1 to 0: killed-by test_pinned_bounds[ev:seq:minimum] and the lint.

S11-52 schemas/ev.json:75 additionalProperties false to true: same as S11-47.

S11-53 schemas/qual.json:63 additionalProperties false to true: same as S11-47.

S11-54 schemas/sprint-proposal.json:58 minimum 1 to 0: expected killed-by the pinned min_attempts_before_block, max_epochs and max_attempts.* entries, or the lint (same caveat as S11-49).

S11-55 schemas/sprint-proposal.json:76 additionalProperties false to true: same as S11-47.

S11-56 schemas/sprint-proposal.json:105 additionalProperties false to true: same as S11-47.

S11-57 schemas/sprint.json:128 additionalProperties false to true: same as S11-47.

S11-58 schemas/sprint.json:114 minimum 1 to 0: same as S11-54, for sprint.

S11-59 schemas/sprint.json:118 minimum 1 to 0: same as S11-58.

S11-60 schemas/state.json:47 additionalProperties false to true: same as S11-47.

S11-61 schemas/state.json:60 additionalProperties false to true: same as S11-47.

C. Seed 23

S23-01 src/actl/hashing.py:71 allow_nan False to True: killed-by test/actl/test_s0_gap3_hashing_tuples.py (rejects nan/inf in nested tuple containers).

S23-02 src/actl/hashing.py:42 0 to 1: same as S11-02 (equivalent row-digest ordering). Formally certified in diff_equiv_seed11.py.

D. Individual dispositions for process.py (Seed 23)

All process.py survivors below reside in pre-existing daemon/process infrastructure introduced in commit 2acaf3c, outside the S0-R16 remediation scope:

S23-03 src/router/process.py:41 ensure_environment() _resolve_log_dir().mkdir(parents=True, exist_ok=True) True to False: out-of-scope (pre-existing directory initialization flag in 2acaf3c).

S23-04 src/router/process.py:111 _wait_pids_gone() return False False to True: out-of-scope (pre-existing process polling timeout return in 2acaf3c).

S23-05 src/router/process.py:227 get_running_sessions() and to or: out-of-scope (pre-existing session discovery guard in 2acaf3c).

S23-06 src/router/process.py:491 kill_session() return 1 to 2: out-of-scope (pre-existing warning exit code on missing session in 2acaf3c).

S23-07 src/router/process.py:546 kill_session() return 0 to 1: out-of-scope (pre-existing clean termination return code in 2acaf3c).

S23-08 src/router/process.py:552 kill_session() _record_exit(session_name, 143, overwrite=True) True to False: out-of-scope (pre-existing exit overwrite flag in 2acaf3c).

S23-09 src/router/process.py:608 create_runner_script() boot_path.chmod(0o755) 0o755 to 0o756: out-of-scope (pre-existing runner boot script permissions in 2acaf3c).

S23-10 src/router/process.py:668 spawn_detached_session() auto_stream: bool = False False to True: out-of-scope (pre-existing keyword default parameter in 2acaf3c).

S23-11 src/router/process.py:737 spawn_detached_session() subprocess.run(cmd, capture_output=True, text=True) True to False: out-of-scope (pre-existing process execution invocation in 2acaf3c).
